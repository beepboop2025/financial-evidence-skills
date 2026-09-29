"""Public packet reader; optional anonymous usage storage is a separate mount."""

import os
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from . import institutional as store
from . import application_usage as applications
from . import funding_contract as contract
from .reliability import now, strict_json, summarize


def create_app(archive=None, events=None):
    archive = Path(archive or os.environ.get("FUNDING_PACKET_DIR", "/data/packets"))
    events = Path(events or os.environ.get("FUNDING_USAGE_DIR", "/data/usage"))
    app = FastAPI(
        title="Funding evidence packets", version="1.0.0", docs_url=None, redoc_url=None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[store.SITE, "https://pro.openbb.co", "https://my.openbb.co"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "If-None-Match"],
        expose_headers=[
            "X-Packet-SHA256",
            "ETag",
            "X-Evidence-Checked-At",
            "X-Usage-Recorded",
        ],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def bounds(request, call_next):
        if len(request.url.query) > 1024:
            return Response(status_code=414)
        if any(
            len(request.headers.get(name, "")) > 1024
            for name in ("Authorization", "If-None-Match")
        ):
            return Response(status_code=431)
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store, no-transform")
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def read(operation):
        try:
            return operation()
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise HTTPException(
                503, "Evidence unavailable or failed validation"
            ) from error

    def identity(request):
        try:
            return applications.identify(
                events, request.headers.get("Authorization"), request.headers
            )
        except PermissionError as error:
            raise HTTPException(
                401, str(error), headers={"WWW-Authenticate": "Bearer"}
            ) from error
        except (OSError, ValueError, sqlite3.Error) as error:
            raise HTTPException(
                503, "Application identity storage unavailable"
            ) from error

    def conditional(request, value, app_identity):
        raw = store.encoded(value)
        etag = '"' + store.digest(raw) + '"'
        matches = [
            part.strip().removeprefix("W/")
            for part in request.headers.get("If-None-Match", "").split(",")
        ]
        unchanged = etag in matches or "*" in matches
        recorded = False
        try:
            recorded = applications.record(
                events, app_identity, value["packet_id"], unchanged=unchanged
            )
        except (OSError, ValueError, sqlite3.Error):
            recorded = "unavailable"
        return Response(
            None if unchanged else raw,
            status_code=304 if unchanged else 200,
            media_type="application/json",
            headers={
                "ETag": etag,
                "Cache-Control": "private, no-cache, must-revalidate, no-transform",
                "Vary": "Authorization",
                "X-Evidence-Checked-At": now(),
                "X-Usage-Recorded": str(recorded).lower(),
            },
        )

    @app.get("/v1/funding/latest")
    def funding_latest(request: Request):
        app_identity = identity(request)
        # Auth, live clocks and every artifact hash precede conditional reuse.
        value = read(lambda: contract.current(archive))
        return conditional(request, value, app_identity)

    @app.get("/v1/funding/changes")
    def funding_changes(request: Request, since: str, until: str | None = None):
        app_identity = identity(request)
        if not store.CAPTURE.fullmatch(since) or (
            until is not None and not store.CAPTURE.fullmatch(until)
        ):
            raise HTTPException(400, "Invalid packet identity")
        latest = read(lambda: contract.current(archive))
        if until is not None and until != latest["packet_id"]:
            raise HTTPException(409, "Latest packet changed; retrieve latest again")
        if not (archive / "packets" / since).is_dir():
            raise HTTPException(404, "Starting packet is outside this forward archive")
        value = read(lambda: contract.changes(archive, since, latest))
        return conditional(request, value, app_identity)

    @app.get("/v1/funding/history")
    def funding_history(request: Request, as_of: str | None = None):
        identity(request)
        latest = read(lambda: contract.current(archive))
        return read(
            lambda: store.history(
                archive, as_of=as_of or latest["archived_at"], limit=96
            )
        )

    @app.post("/v1/applications", status_code=201)
    async def enroll(request: Request):
        if request.headers.get("Origin") not in (None, store.SITE):
            raise HTTPException(403, "Origin not allowed")
        if request.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise HTTPException(415)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 1024:
                raise HTTPException(413)
        try:
            return applications.enroll(events, strict_json(raw), request.headers)
        except OverflowError as error:
            raise HTTPException(
                429, str(error), headers={"Retry-After": "3600"}
            ) from error
        except (ValueError, TypeError) as error:
            raise HTTPException(400, "Explicit measurement consent required") from error
        except (OSError, sqlite3.Error) as error:
            raise HTTPException(503, "Application storage unavailable") from error

    @app.delete("/v1/applications/current")
    def revoke(request: Request):
        if request.headers.get("Origin") not in (None, store.SITE):
            raise HTTPException(403, "Origin not allowed")
        app_identity = identity(request)
        if not app_identity["id"]:
            raise HTTPException(401, "Application credential required")
        try:
            return applications.erase(events, app_identity)
        except (OSError, sqlite3.Error) as error:
            raise HTTPException(503, "Application storage unavailable") from error

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

    @app.get("/widgets.json")
    def funding_widgets():
        from .workspace_config import widgets

        widget = widgets()["evidence_funding_review"]
        widget.pop("mcp_tool", None)
        widget.update(
            name="Verified Funding Packet",
            endpoint="v1/funding/latest",
            description="Nine verified original-publisher observations with their own dates and a common review horizon. Stale or failed latest captures are unavailable.",
        )
        widget["data"]["dataKey"] = "observations"
        return {"funding_automation": widget}

    @app.get("/apps.json")
    def funding_apps():
        return [
            {
                "name": "Funding Evidence Automation",
                "description": "A verified funding packet for the daily research workflow. Public access; no account required.",
                "img": "https://api.seiche.info/openbb/thumbnail.svg",
                "allowCustomization": True,
                "tabs": {
                    "funding": {
                        "id": "funding",
                        "name": "Funding Review",
                        "layout": [
                            {
                                "i": "funding_automation",
                                "x": 0,
                                "y": 0,
                                "w": 40,
                                "h": 14,
                                "state": {"params": {}},
                            }
                        ],
                    }
                },
            }
        ]

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
