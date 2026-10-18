"""Embed shipped M expressions unchanged; mock only their Web.Contents boundary."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMES = ("FinancialEvidenceRows", "FinancialEvidenceFunding", "FinancialEvidenceWatchlist")
PRELUDE = r'''let
    MakeRow = (currency, value, availability, rights) => [
        dataset = "money_markets", product = "seiche", entity_id = currency,
        entity_name = "=2+3", metric = "funding_rate", value = value, unit = "percent",
        as_of = "2026-10-01", availability = availability, source_status = "published",
        source_url = "https://example.invalid/source", source_field = "rate",
        observation_url = null, retrieved_at = "2026-10-18T00:00:00Z",
        content_sha256 = Text.Repeat("a", 64), published_at = null,
        knowledge_time = null, rights_status = rights, context = "fixture only",
        transport_status = "complete", evidence_status = "not_evaluated",
        financial_authority = "none", carrier_verification = "not_performed"],
    QueryFixture = (options) => let
        Q = options[Query], Entity = Q[entity],
        Values = if Entity = "ZZZ" then {} else {
            MakeRow(Entity, 2.5, "published", "allowed"),
            MakeRow(Entity, 0, "published", "allowed"),
            MakeRow(Entity, -1.25, "published", "allowed"),
            MakeRow(Entity, null, "unavailable", "unknown"),
            MakeRow(Entity, 99, "published", "restricted")},
        Base = [schema = "liquidity-lab.openbb-table.v1", dataset = Q[dataset],
            transport_status = "complete", evidence_status = "not_evaluated",
            carrier_verification = "not_performed", next_offset = null,
            returned_rows = List.Count(Values), total_rows = List.Count(Values), results = Values],
        Altered = if Entity = "bad-schema" then Base & [schema = "wrong"]
            else if Entity = "bad-dataset" then Base & [dataset = "bank_risk"]
            else if Entity = "partial" then Base & [transport_status = "partial"]
            else if Entity = "authority" then Base & [evidence_status = "verified"]
            else if Entity = "carrier" then Base & [carrier_verification = "verified"]
            else if Entity = "pagination" then Base & [next_offset = 2000]
            else if Entity = "wrong-count" then Base & [total_rows = 6]
            else Base
        in if Q[limit] <> "2000" or Q[offset] <> "0" then error "Unexpected request bound" else Altered,
    Institution = (slug) => [slug = slug, name = "Fixture bank", institution_type = "bank",
        status = "review_required", latest_period = "2026-06", current_metrics = 0,
        overdue_metrics = 2, coverage_complete = false,
        gaps = {[metric = "lcr", reason = "not_disclosed"]}, warnings = {"source overdue"},
        categories = [liquidity = "unavailable"], content_sha256 = Text.Repeat("b", 64)],
    WatchlistFixture = (options) => let
        Selection = options[Query][selection], Items = Text.Split(Selection, ","),
        Missing = List.Select(Items, each _ = "unknown-bank" or _ = "missing-string"),
        Covered = List.Select(Items, each not List.Contains(Missing, _)),
        Base = [schema = "liquilens.institution-monitoring.v1",
            can_authorize_credit = false, score_authority = false,
            rows = List.Transform(Covered, each Institution(_)),
            not_covered = List.Transform(Missing, each if _ = "missing-string" then _ else [slug = _]),
            as_of = "2026-10-01", limits = {"No credit authority", "Partial source coverage"}],
        Changed = if Selection = "bad-authority" then Base & [can_authorize_credit = true]
            else if Selection = "bad-score" then Base & [score_authority = true]
            else if Selection = "bad-monitor-schema" then Base & [schema = "wrong"]
            else if Selection = "duplicate-bank" then Base & [rows = {Institution(Selection), Institution(Selection)}]
            else if Selection = "absent-bank" then Base & [rows = {}]
            else Base,
        Envelope = [schema = "financial-evidence.workflow-result.v1", workflow = "institutions",
            selection = Selection, evidence = Changed, source_url = "https://example.invalid/watchlist",
            retrieved_at = "2026-10-18T00:00:00Z"]
        in if Selection = "wrong-selection" then Envelope & [selection = "other-bank"] else Envelope,
    #"Web.Contents" = (url as text, options as record) as binary =>
        if url <> "https://agents.seiche.info" or options[Headers][Accept] <> "application/json"
            or options[Timeout] <> #duration(0, 0, 0, 30) then error "Unexpected request contract"
        else Json.FromValue(if options[RelativePath] = "v1/research/api/v1/query" then QueryFixture(options)
            else if options[RelativePath] = "v1/research/api/v1/workflow" then WatchlistFixture(options)
            else error "Unexpected request path"),
'''
ASSERTIONS = r'''
    Rows = FinancialEvidenceRows("money_markets", "USD"),
    Funding = FinancialEvidenceFunding({" usd ", "USD"}),
    Watchlist = FinancialEvidenceWatchlist({"known-bank", "unknown-bank"}),
    Cell = (table, column, index) => Table.Column(table, column){index},
    Checks = {
        [name = "rows_numeric", ok = Value.Is(Cell(Rows, "value", 0), type number) and Cell(Rows, "value", 0) = 2.5],
        [name = "rows_zero", ok = Cell(Rows, "value", 1) = 0],
        [name = "rows_negative", ok = Cell(Rows, "value", 2) = -1.25],
        [name = "rows_null", ok = Cell(Rows, "value", 3) = null],
        [name = "rows_source_and_literal_text", ok = Cell(Rows, "source_url", 0) = "https://example.invalid/source" and Cell(Rows, "entity_name", 0) = "=2+3"],
        [name = "rows_allowlist", ok = (try Table.RowCount(FinancialEvidenceRows("not_allowed")))[HasError]],
        [name = "rows_contract_failures", ok = List.AllTrue(List.Transform({"bad-schema", "bad-dataset", "partial", "authority", "carrier", "pagination", "wrong-count"}, each (try Table.RowCount(FinancialEvidenceRows("money_markets", _)))[HasError]))],
        [name = "funding_selection_normalized_deduplicated", ok = Table.RowCount(Funding) = 5 and Cell(Funding, "selection", 0) = "USD"],
        [name = "funding_multiple_currencies", ok = Table.RowCount(FinancialEvidenceFunding({"USD", "EUR"})) = 10],
        [name = "funding_values", ok = Cell(Funding, "value", 0) = 2.5 and Cell(Funding, "value", 1) = 0 and Cell(Funding, "value", 2) = -1.25],
        [name = "funding_null_separate_from_zero", ok = Cell(Funding, "value", 3) = null and Cell(Funding, "value_state", 3) = "null" and Cell(Funding, "value_state", 1) = "number"],
        [name = "funding_restricted_value_withheld", ok = Cell(Funding, "value", 4) = null and Cell(Funding, "value_state", 4) = "withheld_by_client" and Cell(Funding, "rights_status", 4) = "restricted"],
        [name = "funding_invalid_empty_or_uncovered", ok = (try Table.RowCount(FinancialEvidenceFunding({})))[HasError] and (try Table.RowCount(FinancialEvidenceFunding({"US"})))[HasError] and (try Table.RowCount(FinancialEvidenceFunding({"ZZZ"})))[HasError]],
        [name = "funding_currency_bound", ok = (try Table.RowCount(FinancialEvidenceFunding({"USD", "EUR", "INR", "GBP", "JPY", "CHF"})))[HasError]],
        [name = "watchlist_exact_selection", ok = Table.RowCount(Watchlist) = 2 and Cell(Watchlist, "slug", 0) = "known-bank" and Cell(Watchlist, "slug", 1) = "unknown-bank"],
        [name = "watchlist_unknown_explicit", ok = Cell(Watchlist, "status", 1) = "not_covered" and Cell(Watchlist, "coverage_complete", 1) = false and Cell(Watchlist, "current_metrics", 1) = null],
        [name = "watchlist_zero_and_missing_are_distinct", ok = Cell(Watchlist, "current_metrics", 0) = 0 and Cell(Watchlist, "overdue_metrics", 0) = 2 and Cell(Watchlist, "coverage_complete", 0) = false],
        [name = "watchlist_gaps_and_warnings_preserved", ok = Text.Contains(Cell(Watchlist, "gaps_json", 0), "not_disclosed") and Text.Contains(Cell(Watchlist, "warnings_json", 0), "source overdue") and Text.Contains(Cell(Watchlist, "limits_json", 1), "No credit authority")],
        [name = "watchlist_source_clock", ok = Cell(Watchlist, "source_url", 0) = "https://example.invalid/watchlist" and Cell(Watchlist, "as_of", 0) = "2026-10-01" and Cell(Watchlist, "retrieved_at", 0) = "2026-10-18T00:00:00Z"],
        [name = "watchlist_string_missing_shape", ok = Cell(FinancialEvidenceWatchlist({"missing-string"}), "status", 0) = "not_covered"],
        [name = "watchlist_contract_failures", ok = List.AllTrue(List.Transform({"bad-authority", "bad-score", "bad-monitor-schema", "duplicate-bank", "absent-bank", "wrong-selection"}, each (try Table.RowCount(FinancialEvidenceWatchlist({_})))[HasError]))],
        [name = "watchlist_invalid_inputs", ok = (try Table.RowCount(FinancialEvidenceWatchlist({})))[HasError] and (try Table.RowCount(FinancialEvidenceWatchlist({"BAD"})))[HasError] and (try Table.RowCount(FinancialEvidenceWatchlist({"bad--slug"})))[HasError]]
    },
    Passed = List.AllTrue(List.Transform(Checks, each if _[ok] then true else error ("FAILED: " & _[name])))
in
    if Passed then "OFFICE_NATIVE_ACCEPTANCE_PASS" else error "No checks passed"
'''


def generate(output):
    output.mkdir(parents=True, exist_ok=True)
    sources = {name: (ROOT / "docs" / "office" / (name + ".pq")).read_bytes().decode("utf-8") for name in NAMES}
    bindings = "".join(f"    {name} = (\n{source}\n),\n" for name, source in sources.items())
    positive = PRELUDE + bindings + ASSERTIONS
    (output / "acceptance.query.pq").write_bytes(positive.encode("utf-8"))
    # Identical shipped code and fixture path; one deliberately wrong numeric assertion.
    negative = positive.replace('name = "rows_zero", ok = Cell(Rows, "value", 1) = 0',
                                'name = "negative_control_zero", ok = Cell(Rows, "value", 1) = 999')
    assert negative != positive
    (output / "negative-control.query.pq").write_bytes(negative.encode("utf-8"))
    manifest = {"schema": "financial-evidence.power-query-native-input.v1",
                "source_sha256": {name + ".pq": hashlib.sha256(source.encode()).hexdigest() for name, source in sources.items()},
                "source_lf_sha256": {name + ".pq": hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest() for name, source in sources.items()},
                "fixture_boundary": "Only lexical Web.Contents replacement; shipped query expressions embedded unchanged",
                "assertion_groups": ASSERTIONS.count("name = "), "negative_control": "zero must not equal 999"}
    (output / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(generate(parser.parse_args().output)))
