"""Optional research-installation measurement, isolated from public evidence.

Counts server-prepared tables, never people, independent organizations or revenue.
The existing credential store supplies bounded retention and reviewed attribution.
"""

import asyncio
import argparse
from datetime import timedelta
import hashlib
import json
import sqlite3

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from . import application_usage as usage


def install(app, root, origins):
    async def consent_request(request):
        if root is None:
            raise HTTPException(503, "Optional measurement is not enabled")
        if request.headers.get("origin") and request.headers["origin"] not in origins:
            raise HTTPException(403, "Origin is not allowed")
        raw = b""
        async for chunk in request.stream():
            raw += chunk
            if len(raw) > 1024:
                raise HTTPException(413, "Request is too large")
        return raw

    @app.post("/api/v1/applications", status_code=201)
    async def enroll(request: Request):
        raw = await consent_request(request)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            raise HTTPException(415, "Use application/json")
        try:
            body = json.loads(raw)
            result = await asyncio.to_thread(usage.enroll, root, body, request.headers)
            result["erase"] = "DELETE /api/v1/applications/current"
            result["scope"] = "optional_installation_measurement_not_user_verification"
            return JSONResponse(result, status_code=201, headers={"Cache-Control": "no-store"})
        except (ValueError, UnicodeError) as error:
            raise HTTPException(400, "Explicit measurement consent is required") from error
        except OverflowError as error:
            raise HTTPException(429, "Optional enrollment capacity reached; anonymous research remains available") from error
        except (OSError, sqlite3.Error) as error:
            raise HTTPException(503, "Optional measurement is unavailable") from error

    @app.delete("/api/v1/applications/current")
    async def erase(request: Request):
        await consent_request(request)
        try:
            identity = await asyncio.to_thread(usage.identify, root, request.headers.get("authorization"), request.headers)
            result = await asyncio.to_thread(usage.erase, root, identity)
            return JSONResponse(result, headers={"Cache-Control": "no-store"})
        except PermissionError as error:
            raise HTTPException(401, "A valid measurement credential is required") from error
        except (OSError, ValueError, sqlite3.Error) as error:
            raise HTTPException(503, "Deletion is unavailable; keep measurement disabled and retry") from error

    async def record(request, result):
        if root is None:
            return "disabled"
        # Empty, failed and diagnostic-only results do not become a research cohort.
        if result.transport_status != "complete" or not result.results or result.dataset == "source_health":
            return "not_eligible"
        if not any(row.value is not None and row.availability.lower() in {"published", "available"} for row in result.results):
            return "not_eligible"
        try:
            identity = await asyncio.to_thread(usage.identify, root, request.headers.get("authorization"), request.headers)
            # No entity query text, IP, referrer, user agent or source content is stored.
            signature = {
                "dataset": result.dataset,
                "sources": sorted((item.get("source_url", ""), item.get("content_sha256", "")) for item in result.sources),
                "rows": [(row.entity_id, row.metric, row.as_of, row.value) for row in result.results],
            }
            digest = hashlib.sha256(json.dumps(signature, sort_keys=True, allow_nan=False).encode()).hexdigest()
            recorded = await asyncio.to_thread(usage.record, root, identity, digest)
            return "recorded" if recorded else "aggregate_or_duplicate"
        except PermissionError:
            return "invalid_measurement_key"
        except (OSError, ValueError, TypeError, sqlite3.Error):
            # Measurement storage must never take public research offline.
            return "unavailable"

    return record


def report(root):
    """Thirty UTC dates of opted-in installations; missing people remain unknown."""
    cutoff = (usage.day() - timedelta(days=29)).isoformat()
    with usage.connect(root) as db:
        rows = db.execute(
            "SELECT application, traffic_class, count(DISTINCT day) FROM completions "
            "WHERE day>=? GROUP BY application, traffic_class", (cutoff,)
        ).fetchall()
    return {
        "schema": "financial-evidence.research-growth.v1",
        "evaluated_at": usage.now(),
        "window_start_utc": cutoff,
        "window_days": 30,
        "coverage": "workspace_REST_query_only; consented_installations_are_not_people; MCP_and_other_products_excluded",
        "monthly_active_people": None,
        "paying_customers": None,
        "installations": {
            group: {
                "active": sum(1 for row in rows if row[1] == group),
                "returned_on_multiple_dates": sum(1 for row in rows if row[1] == group and row[2] >= 2),
            } for group in usage.CLASSES
        },
        "usage": usage.report(root),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("report",))
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    print(json.dumps(report(args.directory), indent=2))


if __name__ == "__main__":
    main()
