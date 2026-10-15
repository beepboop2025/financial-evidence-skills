"""Bounded synthetic client measurements; never a feed-age or SLA claim."""
import asyncio
from datetime import datetime, timezone
import math
import statistics
import time

from .client import ProductClient
from .readiness import PROBES


def summarize(values):
    values = sorted(values)
    return {
        "samples": len(values),
        "min_ms": min(values) if values else None,
        "median_ms": statistics.median(values) if values else None,
        "max_ms": max(values) if values else None,
        "p95_ms": values[math.ceil(len(values) * .95) - 1] if len(values) >= 100 else None,
        "p99_ms": values[math.ceil(len(values) * .99) - 1] if len(values) >= 1000 else None,
        "percentile_policy": "nearest_rank; minimum 100 samples for p95 and 1000 for p99",
    }


async def measure_latency(*, platform_url=None, products=None, samples=3, timeout=30,
                          client_factory=ProductClient, monotonic=time.perf_counter):
    selected = list(PROBES) if products is None else list(dict.fromkeys(products))
    if not selected or any(product not in PROBES for product in selected):
        raise ValueError("select one or more reviewed diagnostic products")
    if type(samples) is not int or not 2 <= samples <= 25:
        raise ValueError("samples must be an integer between 2 and 25")
    if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 120:
        raise ValueError("timeout must be between zero and 120 seconds")
    report = {"schema": "financial-evidence.latency.v1", "traffic_class": "synthetic",
              "started_at": datetime.now(timezone.utc).isoformat(),
              "vantage": "calling_host", "samples_requested_per_product": samples,
              "execution_authority": "none", "source_latency": "not_measured",
              "sla_verified": False, "external_adoption": "not_measured",
              "limitations": ["single vantage; no controlled load", "repeated arguments may hit upstream caches",
                              "first call includes session setup; repeat durations include network and upstream work",
                              "source freshness and source-to-consumer event age are separate measurements"]}
    async with client_factory(platform_url=platform_url, mode="test", timeout=timeout,
                              cache_seconds=0, credential=None) as client:
        async def one(product):
            tool, arguments = PROBES[product]
            row = {"product": product, "tool": tool, "calls": []}
            for index in range(samples):
                start = monotonic()
                try:
                    receipt = await asyncio.wait_for(client.call(product, tool, arguments), timeout)
                    error = bool(receipt.get("payload", {}).get("result", {}).get("isError"))
                    result = {"index": index + 1, "status": "tool_error" if error else "passed",
                              "duration_ms": round((monotonic() - start) * 1000, 3),
                              "cache_hit": bool(receipt.get("cache_hit")),
                              "payload_sha256": receipt.get("payload_sha256")}
                    timing = receipt.get("timing", {})
                    result["timing"] = {key: timing[key] for key in (
                        "duration_ms", "clock", "includes_optional_measurement", "session_reused",
                        "initialization_ms", "tool_ms", "queue_ms") if key in timing}
                except Exception as exc:
                    result = {"index": index + 1, "status": "failed",
                              "duration_ms": round((monotonic() - start) * 1000, 3),
                              "reason": "timeout" if isinstance(exc, asyncio.TimeoutError) else type(exc).__name__}
                row["calls"].append(result)
                if result["status"] != "passed":
                    break  # No retries or probe storms after an upstream refusal.
            passed = [call["duration_ms"] for call in row["calls"] if call["status"] == "passed"]
            row["first_call_ms"] = passed[0] if passed else None
            row["repeat_calls"] = summarize(passed[1:])
            row["completed"] = len(passed) == samples
            return row
        report["products"] = await asyncio.gather(*(one(product) for product in selected))
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["status"] = "passed" if all(row["completed"] for row in report["products"]) else "partial"
    return report
