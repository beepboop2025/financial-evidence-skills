#!/usr/bin/env python3
"""Offline correlation review of one complete retained Financial Evidence table.

Install noisefloor==0.4.0. Nothing is fetched or sent to a service. The caller
chooses economically comparable observations and declares their native cadence.
"""
import argparse
import hashlib
import json
from pathlib import Path

from noisefloor import adapters, spectral, __version__


def review(table, *, product, kind, as_of, max_age_seconds, max_gap_seconds,
           window_points=60, step_points=20, max_windows=4, allow_date_only=False):
    """Preserve the full adapter envelope alongside the descriptive assessment."""
    rows = table.get("results") if isinstance(table, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("A nonempty retained table is required")
    if any(not isinstance(row, dict) or row.get("product", "").lower() != product.lower() for row in rows):
        raise ValueError("Review one explicitly selected product; do not mix product scopes")
    measures = {(row.get("dataset"), row.get("metric"), row.get("unit"),
                 row.get("entity_name") if row.get("dataset") == "market_liquidity" else None)
                for row in rows}
    if len(measures) != 1:
        raise ValueError("Choose one dataset, metric and unit; separate liquidity measures")
    adapted = adapters.from_financial_evidence(
        table, kind=kind, max_age_seconds=max_age_seconds,
        max_gap_seconds=max_gap_seconds, allow_date_only=allow_date_only,
    )
    request = {"series": adapted["series"], "as_of": as_of,
               "policy": {"window_points": window_points, "step_points": step_points,
                          "max_windows": max_windows}}
    return {"schema": "financial-evidence.spectral-review.v1", "product": product,
            "noisefloor_version": __version__, "adapter": adapted,
            "request": request, "assessment": spectral.assess(**request),
            "execution_authority": False,
            "scope": "caller-selected comparable panel; no vintage or market-performance certification"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--product", required=True)
    parser.add_argument("--kind", choices=["price", "return", "rate", "spread", "count", "level"], required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--max-age-seconds", type=int, required=True)
    parser.add_argument("--max-gap-seconds", type=int, required=True)
    parser.add_argument("--window-points", type=int, default=60)
    parser.add_argument("--step-points", type=int, default=20)
    parser.add_argument("--max-windows", type=int, default=4)
    parser.add_argument("--allow-date-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args())
    source, output = args.pop("input"), args.pop("output")
    if source.stat().st_size > 16 * 1024 * 1024:
        parser.error("Input exceeds the 16 MiB retained-table limit")
    raw = source.read_bytes()
    result = review(json.loads(raw), **args)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    # Exclusive creation preserves an earlier review and its source identity.
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["assessment"]["status"],
                      "input_sha256": result["input_sha256"], "output": str(output)}))
    return 0 if result["assessment"]["status"] == "assessed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
