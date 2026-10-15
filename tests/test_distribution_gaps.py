import copy
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.audit_distribution_gaps import (
    ROOT, audit, exit_status, expected, fetch, fields_match, load_inputs,
    markdown, probe_url, safe_url, verify,
)


INTEGRITY = "sha512-" + "A" * 86 + "=="


def retrieved(value, *, content_type="application/json"):
    return {"status": "retrieved", "http_status": 200, "content_type": content_type}, json.dumps(value).encode()


def package(name="financial-evidence", version="0.1.8"):
    return {"info": {"name": name, "version": version},
            "urls": [{"yanked": False, "digests": {"sha256": "a" * 64}}]}


class DistributionGapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.ledger = {"entries": [
            {"id": "pypi", "state": "live", "listing_url": "https://pypi.org/project/financial-evidence/"},
            {"id": "pending-directory", "state": "submitted", "submission_url": "https://example.org/submit"}],
            "state_definitions": {"live": "verified listing", "submitted": "pending review", "conditional_artifact": "pending artifact"}}
        self.manifest = {"version": "0.1.8", "last_verified_release": "0.1.8", "release_state": "published"}
        self.channel = {"id": "root-pypi", "kind": "pypi", "identity": "financial-evidence", "required": True,
                        "ledger_ids": ["pypi"], "ledger_required": True, "expected": {"kind": "published_root"}}
        self.catalog = {"schema": "financial-evidence.channel-contracts.v1", "channels": [self.channel]}
        self.write_inputs()

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))

    def write_inputs(self):
        self.write("docs/marketplaces.json", self.ledger)
        self.write("docs/integrations.json", self.manifest)
        self.write("docs/distribution/channel-contracts.json", self.catalog)
        (self.root / "pyproject.toml").write_text('[project]\nname = "financial-evidence"\nversion = "0.1.9"\n')

    def run_audit(self, value=None, **kwargs):
        self.write_inputs()
        return audit(self.root, fetcher=lambda _: retrieved(value if value is not None else package()), **kwargs)

    def test_complete_inventory_includes_submission_without_listing(self):
        report = self.run_audit()
        self.assertEqual({r["id"] for r in report["ledger_inventory"]}, {"pypi", "pending-directory"})
        pending = report["ledger_inventory"][1]
        self.assertEqual((pending["declared_state"], pending["observation"]), ("submitted", "not_monitored"))
        self.assertFalse(pending["publication_acceptance_inferred"])
        self.assertTrue(report["ledger_inventory_complete"])
        self.assertFalse(report["coverage_complete"])
        self.assertIn("pending-directory", markdown(report))

    def test_new_unconfigured_ledger_record_cannot_be_silently_omitted(self):
        self.ledger["entries"].append({"id": "new-channel", "state": "conditional_artifact"})
        report = self.run_audit()
        self.assertEqual(report["ledger_record_count"], 3)
        self.assertEqual(report["ledger_inventory"][-1]["id"], "new-channel")
        self.assertEqual(report["ledger_inventory"][-1]["observation"], "not_monitored")

    def test_duplicate_ledger_or_catalog_records_are_rejected(self):
        for target in ("ledger", "catalog"):
            with self.subTest(target=target):
                if target == "ledger":
                    self.ledger["entries"].append(copy.deepcopy(self.ledger["entries"][0]))
                else:
                    self.catalog["channels"].append(copy.deepcopy(self.channel))
                self.write_inputs()
                with self.assertRaises(ValueError):
                    load_inputs(self.root)
                if target == "ledger":
                    self.ledger["entries"].pop()

    def test_missing_required_channel_is_reported_even_if_registry_is_live(self):
        self.ledger["entries"] = self.ledger["entries"][1:]
        report = self.run_audit()
        self.assertEqual(report["channels"][0]["status"], "current")
        self.assertIn("channel_missing_from_ledger", [f["reason"] for f in report["findings"]])
        self.assertEqual(exit_status(report), 1)

    def test_latest_stale_or_wrong_identity_is_drift_not_http_success(self):
        for value in (package(version="0.1.3"), package(name="unrelated-package")):
            with self.subTest(value=value):
                report = self.run_audit(value)
                self.assertEqual(report["channels"][0]["status"], "drift")
                self.assertEqual(exit_status(report), 1)
        self.assertEqual(self.ledger["entries"][0]["state"], "live")

    def test_html_error_json_and_unbounded_identity_are_unknown_not_publication(self):
        for value in (b"<html>login</html>", b'{"error":"rate limit"}',
                      json.dumps(package(name="x" * 201)).encode()):
            with self.subTest(value=value[:30]):
                report = audit(self.root, fetcher=lambda _: ({"status": "retrieved", "http_status": 200,
                    "content_type": "text/html" if value.startswith(b"<") else "application/json"}, value))
                self.assertEqual(report["channels"][0]["status"], "invalid_response")
                self.assertEqual(exit_status(report), 2)

    def test_yanked_package_is_missing_without_implying_no_users(self):
        value = package()
        value["urls"][0]["yanked"] = True
        report = self.run_audit(value)
        self.assertEqual(report["channels"][0]["reason"], "no_non_yanked_distribution")
        self.assertFalse(report["independent_adoption_verified"])

    def test_provider_outage_is_unknown_while_authoritative_404_is_missing(self):
        for status, code in (("unavailable", 2), ("missing", 1)):
            report = audit(self.root, fetcher=lambda _: ({"status": status, "reason": "provider_failed"}, b""))
            self.assertEqual(exit_status(report), code)
            self.assertEqual(report["ledger_inventory"][0]["declared_state"], "live")

    def test_candidate_source_and_published_component_versions_stay_separate(self):
        self.ledger["entries"].append({"id": "n8n", "state": "live", "version": "0.1.1"})
        other = {"kind": "npm", "identity": "n8n-nodes-financial-evidence", "expected": {"kind": "ledger", "id": "n8n"}}
        self.assertEqual(expected(other, self.ledger, self.manifest, self.root)["version"], "0.1.1")
        report = self.run_audit()
        self.assertEqual(report["channels"][0]["expected"]["version"], "0.1.8")
        self.assertEqual(report["root_release"]["source_version"], "0.1.9")
        self.assertTrue(report["root_release"]["candidate_differs_from_verified"])

    def test_versioned_registry_ledger_uses_its_own_component_version(self):
        self.ledger["entries"][0]["listing_url"] = "https://registry.modelcontextprotocol.io/v0.1/servers/example%2Fwake/versions/0.4.0"
        channel = {"kind": "mcp_registry", "identity": "example/wake", "expected": {"kind": "ledger", "id": "pypi"}}
        self.assertEqual(expected(channel, self.ledger, self.manifest, self.root)["version"], "0.4.0")

    def test_exact_active_latest_registry_identity_required(self):
        channel = {"kind": "mcp_registry"}
        expectation = {"identity": "io.github.example/service", "version": "0.4.0"}
        data = {"server": {"name": expectation["identity"], "version": "0.4.0"},
                "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active", "isLatest": True}}}
        self.assertEqual(verify(channel, expectation, *retrieved(data))[0], "current")
        data["_meta"]["io.modelcontextprotocol.registry/official"]["isLatest"] = False
        self.assertEqual(verify(channel, expectation, *retrieved(data))[0], "drift")
        data["_meta"]["io.modelcontextprotocol.registry/official"]["isLatest"] = 1
        with self.assertRaises(ValueError):
            verify(channel, expectation, *retrieved(data))

    def test_github_tag_check_does_not_claim_latest_or_artifact_install(self):
        expectation = {"identity": "example/repository", "version": "0.1.8"}
        data = {"tag_name": "v0.1.8", "html_url": "https://github.com/example/repository/releases/tag/v0.1.8",
                "draft": False, "prerelease": False, "assets": [{"name": "archive.whl"}]}
        status, _, observed = verify({"kind": "github_release"}, expectation, *retrieved(data))
        self.assertEqual(status, "current")
        self.assertFalse(observed["artifact_bytes_verified"])
        self.assertIn("not_latest", observed["version_check"])
        data["draft"] = True
        self.assertEqual(verify({"kind": "github_release"}, expectation, *retrieved(data))[0], "drift")

    def sdk_candidate(self):
        self.channel.update(id="sdk", kind="npm", ledger_required=False, ledger_ids=[],
                            expected={"kind": "candidate_package", "path": "integrations/ai-sdk/package.json",
                                      "receipt": "docs/distribution/ai-sdk-publication.json"})
        self.write_inputs()
        return {"name": "@moomoo202020/financial-evidence-ai-sdk", "version": "0.1.0"}

    def receipt(self, package):
        self.write("docs/distribution/ai-sdk-publication.json", {
            "schema": "financial-evidence.ai-sdk-publication.v1", "npm_published": True,
            "package": package["name"], "version": package["version"], "source_commit": "a" * 40,
            "observed_at": "2026-01-01T00:00:00Z", "tarball_sha512_integrity": INTEGRITY, "tarball_sha256": "b" * 64})

    def test_unpublished_sdk_does_not_probe_or_claim_absence_or_publication(self):
        package = self.sdk_candidate()
        def unexpected(_):
            self.fail("pending candidate caused a registry request")
        missing = audit(self.root, fetcher=unexpected)
        self.assertEqual(missing["channels"][0]["status"], "pending_publication")
        self.assertEqual(missing["status"], "incomplete")
        self.assertEqual(exit_status(missing), 2)
        self.assertEqual(missing["findings"], [{"channel": "sdk", "severity": "unknown",
                                             "reason": "candidate_artifact_not_present"}])
        self.write("integrations/ai-sdk/package.json", package)
        present = audit(self.root, fetcher=unexpected)
        self.assertEqual(present["channels"][0]["expected"]["version"], "0.1.0")
        self.assertEqual(present["channels"][0]["status"], "pending_publication")
        self.assertEqual(present["status"], "incomplete")
        self.assertEqual(exit_status(present), 2)
        self.assertEqual(present["findings"][0]["reason"], "publication_receipt_missing")
        self.assertFalse(present["independent_adoption_verified"])

    def test_optional_candidate_and_offline_inventory_remain_explicitly_unchecked(self):
        self.sdk_candidate()
        self.channel["required"] = False
        self.write_inputs()
        optional = audit(self.root, fetcher=lambda _: self.fail("pending candidate caused request"))
        self.assertEqual(optional["channels"][0]["status"], "pending_publication")
        self.assertEqual(optional["findings"], [])
        self.channel["required"] = True
        self.write_inputs()
        offline = audit(self.root, offline=True, fetcher=lambda _: self.fail("offline request"))
        self.assertEqual(offline["status"], "not_checked")
        self.assertEqual(offline["channels"][0]["status"], "pending_publication")
        self.assertEqual(exit_status(offline), 0)

    def test_npm_publication_never_marks_separate_vercel_registry_submission_current(self):
        package = self.sdk_candidate()
        actual_catalog = json.loads((ROOT / "docs/distribution/channel-contracts.json").read_text())
        actual_channel = next(channel for channel in actual_catalog["channels"] if channel["id"] == "ai-sdk-npm")
        self.catalog["channels"] = [actual_channel]
        self.ledger["entries"].extend([
            {"id": "vercel-ai-sdk-tools", "state": "submitted",
             "submission_url": "https://github.com/vercel/ai/pull/123"},
            {"id": "financial-evidence-ai-sdk-npm", "state": "live",
             "listing_url": "https://www.npmjs.com/package/@moomoo202020/financial-evidence-ai-sdk"},
        ])
        self.write_inputs()
        self.write("integrations/ai-sdk/package.json", package)
        self.receipt(package)
        value = {**package, "dist": {"integrity": INTEGRITY}}
        report = audit(self.root, fetcher=lambda _: retrieved(value))
        inventory = {row["id"]: row for row in report["ledger_inventory"]}
        self.assertEqual(report["status"], "configured_checks_passed")
        self.assertEqual(inventory["financial-evidence-ai-sdk-npm"]["observation"], "current")
        self.assertEqual(inventory["vercel-ai-sdk-tools"]["observation"], "not_monitored")
        self.assertEqual(inventory["vercel-ai-sdk-tools"]["declared_state"], "submitted")
        self.assertFalse(inventory["vercel-ai-sdk-tools"]["publication_acceptance_inferred"])

    def test_published_sdk_checks_exact_receipt_integrity(self):
        package = self.sdk_candidate()
        self.write("integrations/ai-sdk/package.json", package)
        self.receipt(package)
        value = {**package, "dist": {"integrity": INTEGRITY}}
        good = audit(self.root, fetcher=lambda _: retrieved(value))
        self.assertEqual(good["channels"][0]["status"], "current")
        self.assertFalse(good["channels"][0]["observed"]["artifact_bytes_verified"])
        value["dist"]["integrity"] = "sha512-" + "B" * 86 + "=="
        changed = audit(self.root, fetcher=lambda _: retrieved(value))
        self.assertEqual(changed["channels"][0]["status"], "drift")
        self.assertEqual(changed["channels"][0]["reason"], "registry_integrity_differs_from_publication_receipt")

    def test_receipt_for_different_candidate_is_not_authority(self):
        package = self.sdk_candidate()
        self.write("integrations/ai-sdk/package.json", package)
        self.receipt({**package, "version": "0.0.9"})
        report = audit(self.root, fetcher=lambda _: self.fail("invalid receipt caused request"))
        self.assertEqual(report["channels"][0]["status"], "invalid_configuration")

    def test_invalid_and_future_receipt_clocks_do_not_admit_candidate(self):
        package = self.sdk_candidate()
        self.write("integrations/ai-sdk/package.json", package)
        for clock in (None, "not-a-clock", "2026-01-01T00:00:00", "2999-01-01T00:00:00Z"):
            with self.subTest(clock=clock):
                self.receipt(package)
                path = self.root / "docs/distribution/ai-sdk-publication.json"
                receipt = json.loads(path.read_text())
                receipt["observed_at"] = clock
                path.write_text(json.dumps(receipt))
                report = audit(self.root, fetcher=lambda _: self.fail("invalid clock caused request"))
                self.assertEqual(report["channels"][0]["status"], "invalid_configuration")

    def test_contract_types_and_authority_are_checked(self):
        self.assertFalse(fields_match({"execution_authority": "trade"}, {"execution_authority": "none"}))
        self.assertFalse(fields_match({"market_quotes": 0}, {"market_quotes": False}))
        self.assertTrue(fields_match({"market_quotes": False, "new_field": "allowed"}, {"market_quotes": False}))

    def test_response_payload_is_not_retained(self):
        value = package()
        value["private_or_irrelevant_field"] = "DO-NOT-RETAIN-PAYLOAD"
        report = self.run_audit(value)
        self.assertNotIn("DO-NOT-RETAIN-PAYLOAD", json.dumps(report))

    def test_offline_inventory_is_explicit_and_never_fetches(self):
        report = audit(self.root, offline=True, fetcher=lambda _: self.fail("offline network request"))
        self.assertEqual(report["status"], "not_checked")
        self.assertEqual(exit_status(report), 0)

    def test_repo_catalog_covers_every_current_ledger_record_and_is_valid_offline(self):
        report = audit(ROOT, offline=True, fetcher=lambda _: self.fail("offline network request"))
        actual = json.loads((ROOT / "docs/marketplaces.json").read_text())["entries"]
        self.assertEqual({r["id"] for r in report["ledger_inventory"]}, {r["id"] for r in actual})
        self.assertEqual(report["ledger_record_count"], len(actual))
        self.assertNotIn("invalid_configuration", {r["status"] for r in report["channels"]})


class FetchBoundaryTests(unittest.TestCase):
    def test_only_reviewed_https_hosts_without_credentials_queries_or_ports(self):
        for url in ("http://pypi.org/pypi/a/json", "https://localhost/test", "https://127.0.0.1/test",
                    "https://pypi.org.evil.example/test", "https://token@pypi.org/test",
                    "https://pypi.org:8443/test", "https://pypi.org/test?token=x", "https://pypi.org/test#x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe_url(url)

    def test_fetch_never_follows_redirect_or_adds_credentials(self):
        with patch("scripts.audit_distribution_gaps.subprocess.run", return_value=SimpleNamespace(
                returncode=0, stdout=b"redirect\n302\ntext/html")) as run:
            meta, body = fetch("https://pypi.org/pypi/financial-evidence/json")
        args = run.call_args.args[0]
        self.assertEqual(args[1], "--disable")
        self.assertNotIn("--location", args)
        self.assertFalse(any("Authorization" in arg for arg in args))
        self.assertEqual(run.call_args.kwargs["timeout"], 12)
        self.assertEqual(meta["status"], "unavailable")
        self.assertEqual(body, b"")

    def test_size_and_timeout_fail_closed_without_partial_body(self):
        with patch("scripts.audit_distribution_gaps.subprocess.run", return_value=SimpleNamespace(
                returncode=0, stdout=b"x" * 1_000_001 + b"\n200\napplication/json")):
            meta, body = fetch("https://pypi.org/pypi/financial-evidence/json")
            self.assertEqual((meta["status"], body), ("unavailable", b""))
        with patch("scripts.audit_distribution_gaps.subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 12)):
            self.assertEqual(fetch("https://pypi.org/pypi/financial-evidence/json")[0]["status"], "unavailable")

    def test_scoped_npm_name_is_encoded_into_one_registry_path_component(self):
        url = probe_url({"kind": "npm"}, {"identity": "@scope/package", "version": "1.0.0"})
        self.assertEqual(url, "https://registry.npmjs.org/%40scope%2Fpackage/latest")


if __name__ == "__main__":
    unittest.main()
