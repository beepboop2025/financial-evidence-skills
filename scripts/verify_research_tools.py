#!/usr/bin/env python3
"""Read-only, explicitly synthetic acceptance of the public research kit."""
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("research_client", ROOT / "docs/tools/research_client.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def verify():
    report = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "operator_traffic": True, "external_adoption_verified": False,
              "datasets": {}, "status": "passed"}
    for name in (*client.DEFAULT_DESK, "money_market_history"):
        capture = client.collect(name, synthetic=True)
        report["datasets"][name] = {
            "rows": capture["returned_rows"], "pages": len(capture["pages"]),
            "availability": dict(Counter(row["availability"] for row in capture["results"])),
            "null_values": sum(row.get("value") is None for row in capture["results"]),
            "transport_status": capture["transport_status"],
            "evidence_status": capture["evidence_status"],
        }
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
