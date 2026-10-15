"""Run synthetic recovery drills or a bounded invented-event JSONL replay.

    python examples/trading/feed-pilot.py
    python examples/trading/feed-pilot.py --stdin --at 2026-10-15T00:00:00Z < fixture.jsonl

There is no provider connection, no production admission, and no order authority.
"""
import argparse
from datetime import datetime, timezone
import json
import sys

from financial_evidence.trading.feed_pilot import read_replay_jsonl, replay_events, run_replay_pilot
from financial_evidence.trading.source_contract import utc_time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdin", action="store_true", help="Read invented fixture JSONL from stdin")
    parser.add_argument("--at", help="Timezone-aware synthetic replay clock origin")
    args = parser.parse_args()
    try:
        now = utc_time(args.at) if args.at else datetime.now(timezone.utc)
        result = (replay_events(read_replay_jsonl(sys.stdin.buffer), now=now)
                  if args.stdin else run_replay_pilot(now=now))
    except ValueError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc), "production_eligible": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "passed" or result.get("rejected") == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
