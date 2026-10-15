"""Source permission, clock continuity and recovery are independent admission gates."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest

from financial_evidence.trading.feed_pilot import (
    FeedState, MAX_EVENTS, fixture_contract, read_replay_jsonl, replay_events, run_replay_pilot,
)
from financial_evidence.trading.source_contract import (
    SourceContract, USES, iso_time, load_catalog, qualify_sources, utc_time,
)

NOW = datetime(2026, 10, 15, 14, tzinfo=timezone.utc)


def contract_document():
    contract = fixture_contract(NOW)
    return {"source_id": contract.source_id, "authority": contract.authority, "scope": contract.scope,
            "reviewed_at": iso_time(contract.reviewed_at),
            "review_expires_at": iso_time(contract.review_expires_at), "revoked": False,
            "permissions": {use: dict(row) for use, row in contract.permissions.items()},
            "evidence": [dict(row) for row in contract.evidence]}


def event(kind="snapshot", seq=10, offset=0, **changes):
    result = {"source_id": "synthetic-feed", "kind": kind, "sequence": seq,
              "symbol": "TEST-USD", "event_at": iso_time(NOW + timedelta(milliseconds=offset))}
    if kind != "heartbeat":
        result.update(bid="100", ask="101")
    result.update(changes)
    return result


class ContractTests(unittest.TestCase):
    def test_fixture_never_grants_production_or_trading(self):
        contract = fixture_contract(NOW)
        self.assertTrue(contract.admission("internal_research", NOW, synthetic=True)["allowed"])
        for use in USES:
            self.assertFalse(contract.admission(use, NOW)["allowed"])
        for use in ("trading", "ai_inference", "redistribution", "training"):
            self.assertFalse(contract.admission(use, NOW, synthetic=True)["allowed"])

    def test_future_expired_revoked_and_unknown_use_refused(self):
        contract = fixture_contract(NOW)
        for now in (NOW + timedelta(days=1), NOW - timedelta(days=2)):
            self.assertFalse(contract.admission("internal_research", now, synthetic=True)["allowed"])
        doc = contract_document()
        doc["revoked"] = True
        self.assertFalse(SourceContract.from_mapping(doc).admission("connect", NOW, synthetic=True)["allowed"])
        self.assertFalse(contract.admission("other", NOW, synthetic=True)["allowed"])

    def test_permission_expires_before_review(self):
        doc = contract_document()
        doc["permissions"]["internal_research"]["expires_at"] = iso_time(NOW)
        decision = SourceContract.from_mapping(doc).admission("internal_research", NOW, synthetic=True)
        self.assertEqual(decision["reason"], "permission_expired")

    def test_unknown_permission_defaults_to_denied(self):
        doc = contract_document()
        doc["permissions"]["internal_research"]["status"] = "unknown"
        decision = SourceContract.from_mapping(doc).admission("internal_research", NOW, synthetic=True)
        self.assertEqual(decision["reason"], "permission_unknown")

    def test_malformed_catalog_enum_types_fail_with_sanitized_value_error(self):
        for field in ("scope", "status", "evidence_id"):
            for value in ([], {}):
                doc = contract_document()
                if field == "scope":
                    doc[field] = value
                else:
                    doc["permissions"]["connect"][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    SourceContract.from_mapping(doc)

    def test_approval_requires_evidence_and_cannot_escape_review_window(self):
        for changes in ({"evidence_id": "unrecorded"}, {"expires_at": "2028-01-01T00:00:00Z"},
                        {"expires_at": "2026-01-01T00:00:00Z"}, {"expires_at": "2026-10-16"}):
            with self.subTest(changes=changes):
                doc = contract_document()
                doc["permissions"]["connect"].update(changes)
                with self.assertRaises(ValueError):
                    SourceContract.from_mapping(doc)

    def test_fixture_cannot_grant_other_uses(self):
        doc = contract_document()
        doc["permissions"]["trading"] = dict(doc["permissions"]["connect"])
        with self.assertRaisesRegex(ValueError, "fixture_cannot"):
            SourceContract.from_mapping(doc)

    def test_naive_invalid_future_evidence_and_invalid_hash_rejected(self):
        for field, value in (("reviewed_at", "2026-10-15"), ("review_expires_at", "invalid"),
                             ("revoked", "false"), ("scope", "approved")):
            doc = contract_document()
            doc[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                SourceContract.from_mapping(doc)
        for field, value in (("sha256", ""), ("url", "fixture://user:secret@example.com"),
                             ("url", "https://example.com"),
                             ("retrieved_at", "2099-01-01T00:00:00Z")):
            doc = contract_document()
            doc["evidence"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                SourceContract.from_mapping(doc)

    def test_contract_snapshot_is_immutable(self):
        doc = contract_document()
        contract = SourceContract.from_mapping(doc)
        doc["permissions"]["trading"]["status"] = "approved"
        self.assertFalse(contract.admission("trading", NOW, synthetic=True)["allowed"])
        with self.assertRaises(TypeError):
            contract.permissions["connect"]["status"] = "denied"

    def test_catalog_installed_and_public_copies_equal_and_deny_ai(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual((root / "docs/agents/source-access-contracts.json").read_bytes(),
                         (root / "src/financial_evidence/trading/source-access-contracts.json").read_bytes())
        doc = load_catalog()
        evaluated_at = utc_time(doc["reviewed_at"]) + timedelta(seconds=1)
        report = qualify_sources(now=evaluated_at)
        self.assertEqual(len(report["sources"]), 5)
        self.assertEqual(report["production_sources_admitted_for_ai"], 0)
        self.assertFalse(report["source_data_fetched"])
        self.assertLess(len(json.dumps(report).encode()), 20_000)
        self.assertEqual(report["sources"][0]["admission"]["ai_inference"]["reason"], "permission_denied")

    def test_duplicate_and_oversized_catalog_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.json"
            doc = load_catalog()
            doc["sources"].append(deepcopy(doc["sources"][0]))
            path.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_catalog(path)
            path.write_bytes(b" " * (128 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "too_large"):
                load_catalog(path)


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.feed = FeedState(fixture_contract(NOW), synthetic=True)

    def ingest(self, value, offset=0):
        clock = NOW + timedelta(milliseconds=offset)
        return self.feed.ingest(value, received_at=clock, now=clock)

    def latest(self, offset=0, **kwargs):
        return self.feed.latest("TEST-USD", now=NOW + timedelta(milliseconds=offset), **kwargs)

    def test_snapshot_then_contiguous_update(self):
        self.assertTrue(self.ingest(event())["accepted"])
        self.assertTrue(self.ingest(event("update", 11, 10), 10)["accepted"])
        result = self.latest(20)
        self.assertEqual(result["sequence"], 11)
        self.assertEqual(result["source_age_ms"], 10)
        self.assertEqual(result["source_event_at"], iso_time(NOW + timedelta(milliseconds=10)))
        self.assertFalse(result["production_eligible"])

    def test_gap_quarantines_until_new_enough_snapshot(self):
        self.ingest(event())
        self.assertEqual(self.ingest(event("update", 13, 10), 10)["reason"], "sequence_gap")
        self.assertNotIn("bid", self.latest(10))
        self.assertEqual(self.ingest(event("update", 14, 20), 20)["reason"], "snapshot_required")
        self.assertEqual(self.ingest(event("snapshot", 13, 30), 30)["reason"], "snapshot_behind_observed_sequence")
        self.assertTrue(self.ingest(event("snapshot", 14, 40), 40)["accepted"])

    def test_first_update_and_restart_require_snapshot(self):
        self.assertEqual(self.ingest(event("update", 9))["reason"], "snapshot_required")
        self.ingest(event())
        self.feed.restart()
        self.assertNotIn("bid", self.latest())
        self.assertEqual(self.ingest(event("update", 11, 10), 10)["reason"], "snapshot_required")
        self.assertTrue(self.ingest(event("snapshot", 11, 20), 20)["accepted"])

    def test_replay_duplicate_and_out_of_order_quarantined(self):
        for seq in (10, 9):
            with self.subTest(seq=seq):
                self.setUp()
                self.ingest(event())
                self.assertEqual(self.ingest(event("update", seq, 10), 10)["reason"], "sequence_replay")

    def test_equal_sequence_snapshot_cannot_change_prices_even_after_restart(self):
        for restart in (False, True):
            with self.subTest(restart=restart):
                self.setUp()
                self.ingest(event())
                if restart:
                    self.feed.restart()
                self.assertEqual(self.ingest(event(offset=1, bid="200", ask="201"), 1)["reason"],
                                 "conflicting_snapshot")
                self.assertNotIn("bid", self.latest(1))
                # Decimal representation differences do not invent a conflict.
                self.assertTrue(self.ingest(event(offset=2, bid="100.00", ask="101.000"), 2)["accepted"])

    def test_malformed_json_compatible_event_types_quarantine_without_throwing(self):
        for value in ([], {}, 4, True, None):
            with self.subTest(value=value):
                self.setUp()
                self.ingest(event())
                malformed = event()
                malformed["kind"] = value
                self.assertEqual(self.ingest(malformed)["reason"], "unknown_event_kind")
                self.assertNotIn("bid", self.latest())

    def test_invalid_sequences_and_prices(self):
        for seq in (True, False, -1, 1.2, "10", 2**63):
            with self.subTest(seq=seq):
                self.assertFalse(self.ingest(event(seq=seq))["accepted"])
        for price in (None, True, 0, -1, "NaN", "Infinity", float("nan"), "1e200", "1e-30", "private-value"):
            with self.subTest(price=price):
                result = self.ingest(event(bid=price))
                self.assertFalse(result["accepted"])
                self.assertNotIn("private-value", json.dumps(result))
        self.assertEqual(self.ingest(event(bid="102", ask="101"))["reason"], "crossed_quote")

    def test_naive_missing_future_and_stale_clocks(self):
        for value in (None, "2026-10-15T14:00:00", "not-time", iso_time(NOW + timedelta(seconds=1)),
                      iso_time(NOW - timedelta(seconds=3))):
            with self.subTest(value=value):
                self.assertFalse(self.ingest(event(event_at=value))["accepted"])
        for received, now in ((NOW + timedelta(seconds=1), NOW),
                              (NOW - timedelta(seconds=4), NOW), (NOW, NOW.replace(tzinfo=None))):
            with self.subTest(received=received, now=now):
                self.assertFalse(self.feed.ingest(event(), received_at=received, now=now)["accepted"])

    def test_source_and_receipt_regressions_quarantined(self):
        self.ingest(event(offset=10), 10)
        result = self.ingest(event("update", 11, 0), 20)
        self.assertEqual(result["reason"], "source_clock_regression")
        self.setUp()
        self.ingest(event(offset=10), 10)
        result = self.feed.ingest(event("update", 11, 20), received_at=NOW,
                                  now=NOW + timedelta(milliseconds=20))
        self.assertEqual(result["reason"], "receipt_clock_regression")

    def test_local_clock_regression_denies_quote(self):
        self.ingest(event(offset=10), 10)
        self.assertEqual(self.latest(0)["reason"], "local_clock_regression")
        self.assertNotIn("bid", self.latest(10))

    def test_heartbeat_cannot_make_old_quote_fresh(self):
        self.ingest(event())
        self.assertTrue(self.ingest(event("heartbeat", 10, 1900), 1900)["accepted"])
        current = self.latest(1900)
        self.assertEqual(current["received_at"], iso_time(NOW))
        self.assertEqual(current["last_message_received_at"], iso_time(NOW + timedelta(milliseconds=1900)))
        self.assertEqual(self.latest(2100)["reason"], "quote_stale")
        self.assertNotIn("bid", self.latest(2200))

    def test_heartbeat_must_match_sequence_and_never_recover_gap(self):
        self.ingest(event())
        self.assertEqual(self.ingest(event("heartbeat", 11, 100), 100)["reason"],
                         "heartbeat_continuity_unproven")
        self.assertFalse(self.ingest(event("heartbeat", 11, 200), 200)["accepted"])
        self.assertTrue(self.ingest(event("snapshot", 11, 300), 300)["accepted"])

    def test_silent_stream_requires_snapshot_even_without_polling_latest(self):
        self.ingest(event())
        self.assertEqual(self.ingest(event("update", 11, 4000), 4000)["reason"], "snapshot_required")
        self.assertTrue(self.ingest(event("snapshot", 11, 4100), 4100)["accepted"])
        self.assertEqual(self.latest(8000)["reason"], "heartbeat_timeout")

    def test_expired_rights_and_requested_trading_use_hide_values(self):
        self.ingest(event())
        result = self.latest(use="trading")
        self.assertEqual(result["reason"], "permission_denied")
        self.assertNotIn("bid", result)
        result = self.feed.latest("TEST-USD", now=NOW + timedelta(days=1))
        self.assertEqual(result["reason"], "source_review_expired")

    def test_operator_policy_reload_applies_revocation_and_requires_recovery(self):
        self.ingest(event())
        doc = contract_document()
        doc["revoked"] = True
        self.feed.replace_contract(SourceContract.from_mapping(doc))
        self.assertEqual(self.latest()["reason"], "source_revoked")
        self.assertFalse(self.ingest(event())["accepted"])
        self.feed.replace_contract(fixture_contract(NOW))
        self.assertEqual(self.latest()["reason"], "policy_reload_snapshot_required")
        self.assertTrue(self.ingest(event())["accepted"])
        doc["source_id"] = "different-source"
        with self.assertRaisesRegex(ValueError, "identity_changed"):
            self.feed.replace_contract(SourceContract.from_mapping(doc))

    def test_malformed_requested_use_cannot_leak_quote(self):
        self.ingest(event())
        self.assertEqual(self.latest(use=[])["reason"], "unknown_use")
        self.assertNotIn("bid", self.latest(use=[]))

    def test_production_mode_cannot_use_fixture(self):
        self.feed = FeedState(fixture_contract(NOW))
        self.assertEqual(self.ingest(event())["reason"], "fixture_is_not_production_permission")

    def test_unknown_fields_source_and_oversized_event_deny_without_echo(self):
        self.ingest(event())
        result = self.ingest(event(api_key="PRIVATE-CREDENTIAL"))
        self.assertEqual(result["reason"], "unexpected_event_fields")
        self.assertNotIn("PRIVATE-CREDENTIAL", json.dumps(result))
        self.assertNotIn("bid", self.latest())
        self.assertEqual(self.ingest(event(source_id="coinbase-exchange"))["reason"], "source_mismatch")
        self.assertEqual(self.ingest(event(bid="1" * 5000))["reason"], "event_too_large")

    def test_state_is_bounded_without_eviction_of_existing_symbols(self):
        self.feed = FeedState(fixture_contract(NOW), synthetic=True, max_symbols=1)
        self.ingest(event())
        self.assertEqual(self.ingest(event(symbol="OTHER-USD"))["reason"], "symbol_capacity")
        self.assertEqual(self.latest()["status"], "current")
        self.assertEqual(len(self.feed._states), 1)

    def test_unsubscribed_symbol_query_does_not_quarantine_existing_state(self):
        self.ingest(event())
        self.assertEqual(self.feed.latest("UNKNOWN-USD", now=NOW)["reason"], "snapshot_required")
        self.assertEqual(self.latest()["status"], "current")

    def test_bad_policy_limits_rejected(self):
        for field, value in (("max_symbols", 0), ("max_symbols", True), ("max_symbols", 65),
                             ("max_source_age_seconds", float("nan")),
                             ("heartbeat_timeout_seconds", 0), ("max_future_skew_seconds", -1),
                             ("synthetic", "true"), ("use", "unknown")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                FeedState(fixture_contract(NOW), **{field: value})

    def test_demo_is_deterministic_small_and_not_live_or_adoption_evidence(self):
        result = run_replay_pilot(now=NOW)
        self.assertEqual(result, run_replay_pilot(now=NOW))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(len(result["checks"]), 14)
        for key in ("production_eligible", "live_latency_measured", "source_data_fetched"):
            self.assertFalse(result[key])
        self.assertLess(len(json.dumps(result).encode()), 20_000)

    def test_jsonl_replay_and_bounds(self):
        rows = [{"offset_ms": 0, "event": event()}, {"offset_ms": 10, "event": event("update", 11, 10)}]
        data = BytesIO(b"\n".join(json.dumps(row).encode() for row in rows))
        report = replay_events(read_replay_jsonl(data), now=NOW)
        self.assertEqual(report["accepted"], 2)
        self.assertEqual(report["latest"][0]["sequence"], 11)
        with self.assertRaisesRegex(ValueError, "event_limit"):
            replay_events([rows[0]] * (MAX_EVENTS + 1), now=NOW)
        for raw in (b"x" * 4097, b"not json", b"[]", b"\xff"):
            with self.subTest(raw=raw[:8]), self.assertRaises(ValueError):
                list(read_replay_jsonl(BytesIO(raw)))
        with self.assertRaisesRegex(ValueError, "invalid_replay_record"):
            replay_events([{"offset_ms": True, "event": event()}], now=NOW)


if __name__ == "__main__":
    unittest.main()
