"""Public packet reader; optional anonymous usage storage is a separate mount."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import institutional as store
from .reliability import now, strict_json, summarize


def create_app(archive=None, events=None):
    archive = Path(archive or os.environ.get("FUNDING_PACKET_DIR", "/data/packets"))
    events = Path(events or os.environ.get("FUNDING_USAGE_DIR", "/data/usage"))
    app = FastAPI(
        title="Funding evidence packets", version="1.0.0", docs_url=None, redoc_url=None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[store.SITE],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Packet-SHA256"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def bounds(request, call_next):
        if len(request.url.query) > 1024:
            return Response(status_code=414)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-transform"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def read(operation):
        try:
            return operation()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise HTTPException(
                503, "Evidence unavailable or failed validation"
            ) from error

    @app.get("/healthz")
    def health():
        return {
            "status": "ok",
            "source_commit": os.environ.get(
                "FINANCIAL_EVIDENCE_SOURCE_COMMIT", "unknown"
            ),
            "service": "funding-packets",
        }

    @app.get("/latest")
    def current():
        value = read(lambda: store.latest(archive))
        if not value["available"]:
            raise HTTPException(503, value)
        return value

    @app.get("/history")
    def history(as_of: str | None = None):
        return read(lambda: store.history(archive, as_of=as_of))

    @app.get("/compare")
    def compare(before: str, after: str):
        return read(lambda: store.compare(archive, before, after))

    @app.get("/reliability")
    def reliability():
        # Recompute the tail gap at request time, even if the sampling timer stops.
        observations = read(
            lambda: [
                store.read_json(p)["probe"]
                for p in (archive / "attempts").glob("*.json")
            ]
        )
        return read(lambda: summarize(observations, evaluated_at=now()))

    @app.get("/packets/{identifier}/{name}")
    def download(identifier: str, name: str):
        if name not in ("manifest.json", "review.json", "observations.csv"):
            raise HTTPException(404)
        manifest, review, csv_raw = read(lambda: store.packet(archive, identifier))
        raw = {
            "manifest.json": store.encoded(manifest),
            "review.json": review,
            "observations.csv": csv_raw,
        }[name]
        return Response(
            raw,
            media_type="text/csv" if name.endswith("csv") else "application/json",
            headers={
                "X-Packet-SHA256": store.digest(raw),
                "Link": '<https://beepboop2025.github.io/financial-evidence-skills/funding/sources.md>; rel="license"',
                "Content-Disposition": 'attachment; filename="' + name + '"',
            },
        )

    async def event(request, forget=False):
        if request.headers.get("Origin") != store.SITE:
            raise HTTPException(403, "Origin not allowed")
        if request.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise HTTPException(415)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024:
                raise HTTPException(413)
        try:
            return store.usage_event(events, archive, strict_json(raw), forget=forget)
        except (ValueError, TypeError, OSError, KeyError) as error:
            raise HTTPException(400, "Invalid or unavailable usage event") from error

    @app.post("/events")
    async def record(request: Request):
        return await event(request)

    @app.post("/forget")
    async def forget(request: Request):
        return await event(request, True)

    return app


app = create_app()
