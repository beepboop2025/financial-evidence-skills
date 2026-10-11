"""A source failure must not discard other completed notebook research tasks."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = json.loads((ROOT / "docs/tools/research_desk.ipynb").read_text())
CELLS = {index: "".join(NOTEBOOK["cells"][index]["source"]) for index in (3, 5, 7)}
DATASETS = {"funding": "money_markets", "bank": "bank_risk", "liquidity": "market_liquidity"}


class EvidenceError(ValueError):
    pass


def capture(dataset, *, empty=False):
    return {
        "dataset": dataset,
        "results": [] if empty else [{"dataset": dataset, "value": None, "availability": "withheld"}],
        "returned_rows": 0 if empty else 1,
        "captured_at": "2026-10-11T00:00:00Z",
        "pages": [{"transport_status": "complete", "evidence_status": "not_evaluated"}],
    }


def session(failed=(), *, empty=()):
    calls, exports = [], []
    available = {dataset: capture(dataset, empty=dataset in empty) for dataset in DATASETS.values()}

    def collect(dataset, *, entity, synthetic):
        calls.append((dataset, entity, synthetic))
        if dataset in failed:
            raise EvidenceError("Source retrieval is incomplete")
        return available[dataset]

    def save_capture(result, directory):
        # Record the intended export without touching files or network services.
        exports.append((result, directory))
        return {"dataset": result["dataset"], "row_count": result["returned_rows"]}

    namespace = {
        "research_client": SimpleNamespace(EvidenceError=EvidenceError),
        "collect": collect, "save_capture": save_capture, "SYNTHETIC": True,
        "Path": Path, "datetime": datetime, "timezone": timezone, "json": json,
    }
    return namespace, calls, exports, available


def execute(namespace, cells=(3, 5, 7)):
    with redirect_stdout(io.StringIO()):
        for index in cells:
            exec(compile(CELLS[index], f"research_desk.ipynb:cell-{index}", "exec"), namespace)


class ResearchNotebookTests(unittest.TestCase):
    def test_failed_source_does_not_discard_or_export_other_tasks(self):
        for failed_task, failed_dataset in DATASETS.items():
            with self.subTest(failed_task=failed_task):
                namespace, calls, exports, available = session(failed={failed_dataset})
                execute(namespace)
                successful = set(DATASETS) - {failed_task}
                self.assertEqual(set(namespace["captures"]), successful)
                self.assertEqual(set(namespace["task_errors"]), {failed_task})
                self.assertTrue(namespace["task_errors"][failed_task])
                self.assertEqual(calls, [
                    ("money_markets", "USD", True),
                    ("bank_risk", "ESAF", True),
                    ("market_liquidity", "", True),
                ])
                self.assertEqual({path.name for _, path in exports}, successful)
                self.assertEqual(len(exports), 2)
                for result, path in exports:
                    self.assertIs(result, available[DATASETS[path.name]])
                    self.assertEqual(result["results"][0]["value"], None)
                    self.assertEqual(result["results"][0]["availability"], "withheld")

    def test_all_source_failures_produce_no_successful_captures_or_exports(self):
        namespace, calls, exports, _ = session(failed=set(DATASETS.values()))
        execute(namespace)
        self.assertEqual(len(calls), 3)
        self.assertEqual(namespace["captures"], {})
        self.assertEqual(set(namespace["task_errors"]), set(DATASETS))
        self.assertEqual(exports, [])

    def test_complete_empty_result_remains_distinct_from_a_failed_source(self):
        namespace, _, exports, available = session(failed={"bank_risk"}, empty={"money_markets"})
        execute(namespace)
        self.assertIs(namespace["captures"]["funding"], available["money_markets"])
        self.assertEqual(namespace["captures"]["funding"]["returned_rows"], 0)
        self.assertNotIn("bank", namespace["captures"])
        self.assertEqual({path.name for _, path in exports}, {"funding", "liquidity"})

    def test_unexpected_programming_errors_are_not_reported_as_source_unavailability(self):
        namespace, _, _, _ = session()

        def broken_collect(*args, **kwargs):
            raise RuntimeError("Unexpected implementation failure")

        namespace["collect"] = broken_collect
        with self.assertRaises(RuntimeError):
            execute(namespace, cells=(3,))


if __name__ == "__main__":
    unittest.main()
