"""Optional dedicated ingestion API; never attached to the public evidence API."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import asynccontextmanager, suppress
import asyncio
import hashlib
import json
import logging
import threading
import time

from .store import PermissionDenied


def create_app(store, *, purge_interval=3600):
    """Create an explicitly hosted service. Enrollment and review remain local."""
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse

    if isinstance(purge_interval, bool) or not isinstance(purge_interval, (int, float)) or not 0 <= purge_interval <= 86400:
        raise ValueError("purge interval must be 0..86400 seconds")

    maintenance = {"healthy": False, "last_attempt_at": None, "last_successful_check_at": None,
                   "consecutive_failures": 0, "periodic_expiry_enabled": bool(purge_interval)}
    logger = logging.getLogger(__name__)

    async def check_retention():
        maintenance["last_attempt_at"] = time.time()
        try:
            await asyncio.to_thread(store.expire)
        except Exception:
            maintenance["healthy"] = False
            maintenance["consecutive_failures"] += 1
            # Exception values and tracebacks may contain private storage details.
            logger.warning("learning_retention_check_failed")
        else:
            maintenance["healthy"] = True
            maintenance["consecutive_failures"] = 0
            maintenance["last_successful_check_at"] = time.time()

    @asynccontextmanager
    async def lifespan(app):
        async def cleanup():
            while True:
                await asyncio.sleep(purge_interval)
                await check_retention()
        await check_retention()
        task = asyncio.create_task(cleanup()) if purge_interval else None
        app.state.retention_task = task
        try:
            yield
        finally:
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="Optional Financial Agent Learning", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.maintenance = maintenance
    app.state.retention_task = None
    windows = OrderedDict()
    lock = threading.Lock()

    @app.middleware("http")
    async def no_cache(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    async def credential(request):
        raw = request.headers.get("authorization", "")
        if not raw.startswith("Bearer ") or len(raw) > 140:
            raise HTTPException(401, "enrolled bearer credential required")
        value = raw[7:]
        try:
            await asyncio.to_thread(store.describe, value)
        except PermissionDenied:
            raise HTTPException(401, "invalid credential") from None
        except Exception:
            raise HTTPException(503, "learning storage unavailable") from None
        key, now = hashlib.sha256(value.encode()).hexdigest(), time.monotonic()
        with lock:
            start, count = windows.pop(key, (now, 0))
            if now - start >= 60:
                start, count = now, 0
            windows[key] = (start, count + 1)
            while len(windows) > 4096:
                windows.popitem(last=False)
        if count >= 600:
            raise HTTPException(429, "tenant request allowance reached", headers={"Retry-After": "60"})
        return value

    async def body(request):
        if request.headers.get("content-encoding", "identity").lower() != "identity":
            raise HTTPException(415, "compressed request bodies are not supported")
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
            raise HTTPException(415, "application/json required")
        chunks, length = [], 0
        async for chunk in request.stream():
            length += len(chunk)
            if length > 65536:
                raise HTTPException(413, "maximum request body is 64 KiB")
            chunks.append(chunk)
        try:
            result = json.loads(b"".join(chunks))
        except (UnicodeError, ValueError):
            raise HTTPException(400, "invalid JSON") from None
        if not isinstance(result, dict):
            raise HTTPException(400, "JSON object required")
        return result

    async def invoke(function, *args, **kwargs):
        try:
            return await asyncio.to_thread(function, *args, **kwargs)
        except PermissionDenied:
            raise HTTPException(403, "required purpose permission is inactive") from None
        except (TypeError, ValueError):
            raise HTTPException(422, "record rejected by bounded schema, consent, timing or isolation checks") from None
        except OverflowError:
            raise HTTPException(429, "tenant storage allowance reached") from None
        except Exception:
            raise HTTPException(503, "learning storage unavailable") from None

    # Request lives inside the optional import, so avoid resolving a postponed
    # annotation against module globals when FastAPI constructs each route.
    async def health():
        task = app.state.retention_task
        running = task is not None and not task.done() if purge_interval else True
        healthy = maintenance["healthy"] and running
        return JSONResponse(status_code=200 if healthy else 503, content={
            "status": "ok" if healthy else "degraded", "schema": "financial-evidence.learning.v1",
            "explicit_enrollment_required": True, "training_admission": "local_operator_review_only",
            "retention": {**maintenance, "worker_running": running},
        })

    app.add_api_route("/health", health, methods=["GET"])

    async def submit_event(request):
        token = await credential(request)
        return await invoke(store.record_tool, token, await body(request))

    async def submit_decision(request):
        token = await credential(request)
        return await invoke(store.record_decision, token, await body(request))

    async def submit_outcome(request):
        token = await credential(request)
        return await invoke(store.record_outcome, token, await body(request))

    async def me(request):
        return await invoke(store.describe, await credential(request))

    async def report(request):
        return await invoke(store.report, await credential(request))

    async def withdraw(request):
        token = await credential(request)
        value = await body(request)
        if set(value) - {"purposes", "delete"} or ("delete" in value and not isinstance(value["delete"], bool)):
            raise HTTPException(422, "invalid withdrawal schema")
        return await invoke(store.withdraw, token, **value)

    async def delete(request):
        return await invoke(store.delete_tenant, await credential(request))

    for path, endpoint, method in (("/v1/events", submit_event, "POST"), ("/v1/decisions", submit_decision, "POST"),
                                   ("/v1/outcomes", submit_outcome, "POST"), ("/v1/me", me, "GET"),
                                   ("/v1/report", report, "GET"), ("/v1/withdraw", withdraw, "POST"),
                                   ("/v1/me", delete, "DELETE")):
        endpoint.__annotations__["request"] = Request
        app.add_api_route(path, endpoint, methods=[method])
    return app
