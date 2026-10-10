"""Separate, on-demand research capture for a Hummingbot/Freqtrade operator."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from financial_evidence.agents import EvidenceAgentClient
from forward_evidence import capture, for_decision, load, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("capture", help="Fetch one bounded evidence page")
    collect.add_argument("--dataset", choices=["money_markets", "bank_risk", "market_liquidity"], default="money_markets")
    collect.add_argument("--entity", default="USD")
    collect.add_argument("--output", type=Path, required=True)
    inspect = sub.add_parser("inspect", help="Read a retained capture for human review")
    inspect.add_argument("path", type=Path)
    inspect.add_argument("--decision-at", default=None, help="UTC-offset ISO timestamp; defaults to now")
    args = parser.parse_args()
    if args.command == "capture":
        with EvidenceAgentClient() as client:
            snapshot = capture(client.query(args.dataset, entity=args.entity, limit=5))
        print(json.dumps(save(snapshot, args.output), indent=2))
        return 0 if snapshot["packet"]["transport_status"] == "complete" else 2
    snapshot = for_decision(load(args.path), decision_at=args.decision_at or datetime.now(timezone.utc).isoformat())
    print(json.dumps(snapshot, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
