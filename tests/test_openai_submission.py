"""Submission ZIP contracts, independent of runtime release and model acceptance."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("openai_submission", ROOT / "scripts/build_openai_submission.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
FE_TOOLS = {
    "financial_evidence_workflow", "financial_evidence_datasets",
    "financial_evidence_funding_review", "financial_evidence_query",
    "financial_evidence_sources", "financial_evidence_route",
    "financial_evidence_packet", "financial_evidence_agent_query",
    "financial_evidence_review",
}


def check_review(test, manifest, tools):
    test.assertNotIn("review", manifest["interface"])
    review = manifest["extensions"]["com.openai"]["review"]
    cases = review["test_cases"]
    test.assertEqual(len(cases["positive"]), 5)
    test.assertEqual(len(cases["negative"]), 3)
    for case in cases["positive"]:
        test.assertEqual(set(case), {"description", "prompt", "tools_triggered", "expected_behavior"})
        test.assertTrue(all(isinstance(v, str) and v.strip() for v in case.values()))
        triggered = {name.strip() for name in case["tools_triggered"].split(",")}
        test.assertTrue(triggered)
        test.assertLessEqual(triggered, tools)
    for case in cases["negative"]:
        test.assertEqual(set(case), {"description", "prompt"})
        test.assertTrue(all(isinstance(v, str) and v.strip() for v in case.values()))
    test.assertFalse(review["commerce"])
    # A video URL may be added only when an actual walkthrough exists.
    test.assertNotIn("demo_recording_url", review)


class OpenAISubmissionTests(unittest.TestCase):
    def test_candidate_contains_review_cases_and_unchanged_runtime_assets(self):
        outputs = builder.build()
        body = next(v for k, v in outputs.items() if k.endswith(".zip"))
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertEqual(set(archive.namelist()), set(builder.FILES) | {".codex-plugin/plugin.json"})
            manifest = json.loads(archive.read(".codex-plugin/plugin.json"))
            check_review(self, manifest, FE_TOOLS)
            self.assertEqual(manifest["name"], "financial-evidence")
            self.assertEqual(manifest["version"], "0.1.17")
            self.assertEqual(manifest["mcpServers"], "./.mcp.json")
            for name in builder.FILES:
                self.assertEqual(archive.read(name), (ROOT / name).read_bytes(), name)
            for key in ("logo", "composerIcon"):
                self.assertIn(manifest["interface"][key].removeprefix("./"), archive.namelist())

    def test_candidate_is_reproducible_and_does_not_claim_model_acceptance(self):
        for name, expected in builder.build().items():
            self.assertEqual((ROOT / name).read_bytes(), expected, name)
            if name.endswith(".json"):
                receipt = json.loads(expected)
                self.assertEqual(receipt["review_cases_status"], "configured_not_model_tested")
                self.assertEqual(receipt["demo_recording_status"], "not_recorded")
                self.assertFalse(receipt["official_directory_approved"])


if __name__ == "__main__":
    unittest.main()
