import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import test from "node:test";

const script = fs.readFileSync(new URL("../docs/tools/FinancialEvidenceSheets.gs", import.meta.url), "utf8");

function row(value = 0, extra = {}) {
  return {
    dataset: "money_markets", product: "Seiche", entity_id: "US-USD", entity_name: "US dollar",
    metric: "rate", value, unit: "%", as_of: "2026-10-08", availability: "AVAILABLE",
    source_status: "FRESH", source_url: "https://api.seiche.info/api/v2/money-markets",
    source_field: "/markets/0/benchmark/value", observation_url: "https://example.org/rates",
    retrieved_at: "2026-10-11T00:00:00Z", content_sha256: "sha256:" + "a".repeat(64),
    published_at: "2026-10-09T00:00:00Z", knowledge_time: "2026-10-10T00:00:00Z",
    rights_status: "allowed", context: "Source context", transport_status: "complete",
    evidence_status: "not_evaluated", financial_authority: "none", carrier_verification: "not_performed",
    ...extra,
  };
}

function page(extra = {}) {
  return {
    schema: "liquidity-lab.openbb-table.v1", dataset: "money_markets",
    results: [row(0), row(null, {availability: "unavailable", rights_status: null})],
    total_rows: 2, returned_rows: 2, offset: 0, limit: 50, next_offset: null,
    transport_status: "complete", status_semantics: "transport_only", evidence_status: "not_evaluated",
    carrier_verification: "not_performed", diagnostics: [],
    sources: [{source_url: "https://api.seiche.info/api/v2/money-markets", ok: true,
      content_sha256: "sha256:" + "a".repeat(64), cache: {hit: true, age_seconds: 10},
      source_reported: {state: [{name: "response_status", value: "PARTIAL"}],
        clocks: [{name: "generated_at", value: "2026-10-10T23:59:00Z"}]}}],
    ...extra,
  };
}

function runtime(document = page(), options = {}) {
  const calls = [];
  const context = vm.createContext({
    UrlFetchApp: {fetch(url, config) {
      calls.push({url, config});
      if (options.networkError) throw new Error("private or provider-specific exception text");
      const raw = options.raw ?? JSON.stringify(document);
      return {
        getResponseCode: () => options.status ?? 200,
        getHeaders: () => ({"Content-Type": options.type ?? "application/json; charset=utf-8"}),
        getContent: () => ({length: options.bytes ?? Buffer.byteLength(raw)}),
        getContentText: () => raw,
      };
    }},
  });
  vm.runInContext(script, context);
  return {run: (...args) => JSON.parse(JSON.stringify(context.FINANCIAL_EVIDENCE(...args))), calls};
}

function metadata(table) { return Object.fromEntries(table.slice(0, 13).map(([key, value]) => [key, value])); }
function records(table) { return table.slice(14).map(values => Object.fromEntries(table[13].map((key, i) => [key, values[i]]))); }

test("one page preserves source clocks, zero, null and provenance with a rectangular spill", () => {
  const {run, calls} = runtime();
  const table = run();
  const rows = records(table);
  assert.equal(calls.length, 1);
  assert.equal(table.length, 16);
  assert.ok(table.every(row => row.length === 24));
  assert.equal(rows[0].value, 0);
  assert.equal(rows[0].value_state, "number");
  assert.equal(rows[1].value, "");
  assert.equal(rows[1].value_state, "null");
  assert.equal(rows[1].rights_status, "");
  assert.equal(rows[0].as_of, "2026-10-08");
  assert.equal(rows[0].unit, "%");
  assert.equal(rows[0].published_at, "2026-10-09T00:00:00Z");
  assert.equal(rows[0].knowledge_time, "2026-10-10T00:00:00Z");
  assert.equal(rows[0].source_field, "/markets/0/benchmark/value");
  assert.equal(metadata(table).page_scope, "all_matching_rows_in_this_response");
  const sources = JSON.parse(metadata(table).source_provenance_json);
  assert.equal(sources[0].source_reported.state[0].value, "PARTIAL");
  assert.equal(sources[0].cache.age_seconds, 10);
});

test("explicit restrictions never leak numbers while genuine negative numbers remain numeric", () => {
  for (const field of ["rights_status", "availability", "source_status"]) {
    for (const state of ["restricted", "WITHHELD", "not available", "derived-only", "review_required"]) {
      const rows = records(runtime(page({results: [row(42, {[field]: state}), row(-2)]})).run());
      assert.equal(rows[0].value, "");
      assert.equal(rows[0].value_state, "withheld_by_client");
      assert.equal(rows[0][field], state);
      assert.equal(rows[1].value, -2);
    }
  }
  const table = runtime(page({results: [row(42, {publication_allowed: false}), row(null)]})).run();
  assert.equal(metadata(table).client_withheld_numeric_rows, 1);
});

test("a partial source response and a paginated response remain visibly different", () => {
  const partial = runtime(page({transport_status: "partial", diagnostics: [{availability: "source_unavailable"}]})).run();
  assert.match(metadata(partial).transport_status, /^partial /);
  assert.match(metadata(partial).diagnostics_json, /source_unavailable/);
  const paged = runtime(page({limit: 2, total_rows: 3, next_offset: 2}));
  const table = paged.run("money_markets", "", 2);
  assert.equal(metadata(table).page_scope, "partial_dataset_page");
  assert.equal(metadata(table).next_offset, 2);
  assert.equal(paged.calls.length, 1, "must not automatically fetch next page");
  const finalPage = runtime(page({results: [row(1)], returned_rows: 1, offset: 2, limit: 2, total_rows: 3}));
  assert.equal(metadata(finalPage.run("money_markets", "", 2, 2)).page_scope, "partial_dataset_page");
});

test("empty matching results and unavailable retrieval retain status without manufactured rows", () => {
  for (const transport_status of ["complete", "unavailable"]) {
    const table = runtime(page({results: [], total_rows: 0, returned_rows: 0, transport_status,
      sources: [{source_url: "https://api.seiche.info/api/v2/money-markets", ok: false}]})).run();
    assert.equal(table.length, 14);
    assert.equal(records(table).length, 0);
    assert.match(metadata(table).transport_status, new RegExp("^" + transport_status));
  }
});

test("remote source strings cannot become formulas, including leading whitespace", () => {
  for (const text of ["=IMPORTXML(\"https://bad.invalid\")", " +SUM(1,2)", "-2+3", "@SUM(1)", "\tformula", "\ntext"]) {
    const rows = records(runtime(page({results: [row(0, {context: text, entity_name: text}), row(null)]})).run());
    assert.equal(rows[0].context, "'" + text);
    assert.equal(rows[0].entity_name, "'" + text);
  }
});

test("fixed endpoint, encoded entity, no redirects, and refresh values are never sent", () => {
  const {run, calls} = runtime();
  run("money_markets", "US&dataset=bank_risk", 50, 0, "private manual refresh counter");
  const url = new URL(calls[0].url);
  assert.equal(url.origin, "https://api.seiche.info");
  assert.equal(url.pathname, "/openbb/api/v1/query");
  assert.equal(url.searchParams.get("entity"), "US&dataset=bank_risk");
  assert.equal(url.searchParams.get("dataset"), "money_markets");
  assert.deepEqual([...url.searchParams.keys()].sort(), ["dataset", "entity", "limit", "offset"]);
  assert.equal(calls[0].config.followRedirects, false);
  assert.equal(calls[0].config.validateHttpsCertificates, true);
  assert.equal(calls[0].config.method, "get");
  assert.ok(!JSON.stringify(calls).includes("private manual"));
});

test("unsupported or unbounded inputs fail before any request", () => {
  const invalid = [["https://other.invalid"], ["other"], ["money_markets", "x".repeat(101)],
    ["money_markets", []], ["money_markets", "", 201], ["money_markets", "", 0],
    ["money_markets", "", true], ["money_markets", "", 1.5], ["money_markets", "", 50, -1],
    ["money_markets", "", 50, 100001], ["money_markets", "", 50, 0, [[1]]],
    ["money_markets", "", 50, 0, Infinity]];
  for (const args of invalid) {
    const {run, calls} = runtime();
    assert.throws(() => run(...args));
    assert.equal(calls.length, 0);
  }
});

test("HTTP, redirects, malformed JSON, oversized responses and network errors fail visibly", () => {
  for (const options of [{status: 302}, {status: 429}, {status: 503}, {type: "text/html"},
    {raw: "<html>challenge</html>"}, {bytes: 4 * 1024 * 1024 + 1}, {networkError: true}]) {
    const {run, calls} = runtime(page(), options);
    assert.throws(() => run(), error => !error.message.includes("private or provider"));
    assert.equal(calls.length, 1);
  }
});

test("pagination and authority inconsistencies are rejected instead of returning misleading data", () => {
  for (const change of [{schema: "other"}, {dataset: "bank_risk"}, {total_rows: 3},
    {next_offset: 0}, {offset: 1}, {limit: 51}, {returned_rows: 1}, {total_rows: 1.5},
    {sources: []}, {sources: [{source_url: "http://insecure.invalid"}]}, {diagnostics: null},
    {carrier_verification: "verified"}, {evidence_status: "approved"}, {status_semantics: "risk_score"},
    {results: [row(1, {dataset: "bank_risk"}), row(2)]},
    {results: [row(1, {financial_authority: "approved"}), row(2)]},
    {results: [row("0"), row(2)]}]) {
    assert.throws(() => runtime(page(change)).run());
  }
  const raw = JSON.stringify(page()).replace('"value":0', '"value":1e999');
  assert.throws(() => runtime(page(), {raw}).run());
});

test("oversized provenance is rejected rather than silently truncated", () => {
  const doc = page();
  doc.sources[0].source_reported.extra = "x".repeat(45001);
  assert.throws(() => runtime(doc).run(), /too large/);
});

test("live public response passes the same Apps Script parser (not a Google-native execution)", {
  skip: process.env.FINANCIAL_EVIDENCE_LIVE_CHECK !== "1",
}, async () => {
  const url = "https://api.seiche.info/openbb/api/v1/query?dataset=money_markets&entity=&limit=2&offset=0";
  const response = await fetch(url, {redirect: "error", signal: AbortSignal.timeout(20000), headers: {
    Accept: "application/json", "User-Agent": "Financial-Evidence-Operator-Verification/1.0",
    "X-Liquilens-Traffic-Class": "synthetic",
  }});
  assert.equal(response.status, 200);
  const raw = await response.text();
  const table = runtime(null, {raw, type: response.headers.get("content-type")}).run("money_markets", "", 2);
  const meta = metadata(table);
  assert.equal(meta.page_scope, "partial_dataset_page");
  assert.equal(records(table).length, 2);
  assert.ok(records(table).every(row => row.financial_authority === "none"));
  console.log(JSON.stringify({check: "live_parser_only", google_native_verified: false,
    fetched_at_utc: meta.fetched_at_utc, transport_status: meta.transport_status,
    page_counts: meta.page_counts, next_offset: meta.next_offset}));
});
