#!/usr/bin/env python3
"""Evaluate an explicitly exported, reviewed finance dataset; no network calls."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from financial_evidence.learning.cli import private_write, read_json
from financial_evidence.learning.evaluation import evaluate
from financial_evidence.learning import LearningStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset")
    parser.add_argument("--store", required=True, help="original learning store, to recheck withdrawal and expiry")
    parser.add_argument("--entity")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dataset = read_json(args.dataset)
    LearningStore(args.store).validate_snapshot(dataset)
    result = evaluate(dataset, entity=args.entity)
    private_write(args.output, result)
    print(json.dumps({key: value for key, value in result.items() if key not in {"models", "test_predictions"}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
