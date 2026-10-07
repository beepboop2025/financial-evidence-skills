"""One-process REST, OpenBB Workspace and Streamable HTTP MCP backend."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
from contextlib import asynccontextmanager
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .agents import EvidenceAgentClient
from .models import QueryResult
from .funding_archive import read_export, read_review
from .release import WORKSPACE_VERSION, release_identity
from .service import EvidenceService
from .tables import Dataset, dataset_catalog
from .workspace_config import SCOPE, THUMBNAIL, apps, widgets
from .workspace_mcp import create_mcp
from .workspace_usage import install as install_usage


def create_app(
    *, service: EvidenceService | None = None, base_url: str | None = None,
    usage_dir: str | None = None,
) -> FastAPI:
    base_url = (
        base_url or os.getenv("FINANCIAL_EVIDENCE_BASE_URL", "http://127.0.0.1:6900")
    ).rstrip("/")
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or (parsed.path and not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)+", parsed.path))
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "base_url must be an HTTP(S) origin with an optional simple path prefix, without credentials, query or fragment"
        )
    origin = f"{parsed.scheme}://{parsed.netloc}"
    origins = [
        "https://pro.openbb.co",
        "https://my.openbb.co",
        "https://beepboop2025.github.io",
        "http://localhost:6900",
        "http://127.0.0.1:6900",
        origin,
    ]
    origins += [
        value.strip()
        for value in os.getenv("FINANCIAL_EVIDENCE_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    ]
    for origin in origins:
        parts = urlsplit(origin)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.path
            or parts.query
            or parts.fragment
            or parts.username
            or parts.password
            or "*" in origin
        ):
            raise ValueError("Allowed origins must be explicit HTTP(S) origins")
    owned_service = service is None
    service = service or EvidenceService()
    identity = release_identity()
    agent_client = EvidenceAgentClient(service)
    mcp = create_mcp(
        service,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", parsed.netloc],
        allowed_origins=origins,
    )
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        try:
            async with mcp.session_manager.run():
                yield
        finally:
            if owned_service:
                await asyncio.to_thread(service.close)

    app = FastAPI(
        title="Financial Evidence for OpenBB",
        version=WORKSPACE_VERSION,
        root_path=parsed.path,
        lifespan=lifespan,
        description="Seven source-cited datasets, Workspace widgets and read-only MCP. No API key required.",
    )
    app.state.evidence_service = service
    app.state.mcp = mcp
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]", parsed.hostname],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(dict.fromkeys(origins)),
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "MCP-Protocol-Version",
            "Mcp-Session-Id",
            "Last-Event-ID",
            "Authorization",
            "X-Liquilens-Traffic-Class",
        ],
        expose_headers=[
            "Mcp-Session-Id",
            "X-Financial-Evidence-Capture",
            "X-Data-Readiness",
            "X-Release-Identity",
            "ETag",
            "X-Financial-Evidence-Measurement",
        ],
        allow_credentials=False,
    )
    record_usage = install_usage(app, usage_dir or os.getenv("FINANCIAL_EVIDENCE_USAGE_DIR"), origins)

    @app.exception_handler(ValueError)
    async def bad_query(request: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.get("/")
    async def index() -> dict:
        return {
            "name": app.title,
            "version": __version__,
            "release": identity,
            "docs": base_url + "/docs",
            "workspace_backend": base_url,
            "mcp": base_url + "/mcp",
            "authentication": "none",
            "dataset_count": len(dataset_catalog()),
        }

    @app.get("/healthz")
    async def health() -> dict:
        return {
            "status": "ok",
            "scope": "backend_process_only",
            "upstream_status": "not_checked",
            "release_id": identity["release_id"],
        }

    @app.get("/api/v1/release")
    async def release() -> dict:
        """Build identity; this does not assert data freshness or readiness."""
        return identity

    @app.get("/api/v1/funding-review")
    async def funding_review() -> dict:
        """Dated funding review with explicit alignment scope, capture age and exceptions."""
        return await asyncio.to_thread(read_review)

    @app.get("/api/v1/funding-review.csv")
    async def funding_review_csv():
        """Latest verified export; stale or unavailable captures return 503."""
        review, data = await asyncio.to_thread(read_export)
        if data is None:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "capture_unavailable_or_stale",
                    "review": base_url + "/api/v1/funding-review",
                },
            )
        return Response(
            data,
            media_type="text/csv",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": 'attachment; filename="funding-observations.csv"',
                "X-Financial-Evidence-Capture": review["capture_id"],
                "X-Data-Readiness": review["data_readiness"],
                "X-Release-Identity": review["release_identity"],
                "X-Funding-Review-Scope": review["review_scope"],
                "X-Funding-Review-As-Of": review["review_asof"] or "unknown",
                "ETag": '"' + hashlib.sha256(data).hexdigest() + '"',
            },
        )

    @app.get("/widgets.json", include_in_schema=False)
    async def get_widgets():
        return widgets()

    @app.get("/apps.json", include_in_schema=False)
    async def get_apps():
        return apps(base_url)

    @app.get("/guide", response_class=PlainTextResponse)
    async def guide() -> str:
        return SCOPE

    @app.get("/thumbnail.svg", include_in_schema=False)
    async def thumbnail():
        return Response(
            THUMBNAIL,
            media_type="image/svg+xml",
            headers={"Cache-Control": "public,max-age=86400"},
        )

    @app.get("/api/v1/datasets")
    async def datasets() -> list[dict[str, Any]]:
        """List datasets and coverage without contacting upstream sources."""
        return dataset_catalog()

    @app.get("/api/v1/query")
    async def query(
        request: Request,
        response: Response,
        dataset: Dataset,
        entity: Annotated[
            str,
            Query(max_length=100, description="Entity ID or name contains this text."),
        ] = "",
        start_date: str = "",
        end_date: str = "",
        limit: Annotated[int, Query(ge=1, le=2000)] = 200,
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
    ) -> QueryResult:
        """Return bounded table rows, explicit pagination, source metadata and diagnostics."""
        result = await asyncio.to_thread(
            service.query,
            dataset,
            entity=entity or None,
            start_date=start_date or None,
            end_date=end_date or None,
            limit=limit,
            offset=offset,
        )
        value = QueryResult.model_validate(result)
        response.headers["X-Financial-Evidence-Measurement"] = await record_usage(request, value)
        response.headers["Cache-Control"] = "no-store"
        return value

    @app.get("/api/v1/sources")
    async def sources() -> QueryResult:
        """Inspect upstream retrieval and publisher clocks; transport only."""
        return QueryResult.model_validate(
            await asyncio.to_thread(service.query, "source_health")
        )

    @app.get("/api/v1/packet")
    async def packet(topics: Annotated[str, Query(max_length=150)]) -> dict[str, Any]:
        """Fetch original documents: up to 4 MiB for the money-market atlas, 1 MiB for other sources."""
        return await asyncio.to_thread(service.packet, [topics])

    @app.get("/api/v1/agent-query")
    async def agent_query(
        dataset: Dataset, entity: Annotated[str, Query(max_length=100)] = "",
        start_date: str = "", end_date: str = "",
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
        offset: Annotated[int, Query(ge=0, le=100000)] = 0,
        previous_revision: Annotated[str, Query(pattern=r"^(?:[0-9a-f]{64})?$", max_length=64)] = "",
    ) -> dict[str, Any]:
        """Compact cited rows with a repeat-call revision, retaining source clocks and gaps."""
        return await asyncio.to_thread(agent_client.query, dataset, entity,
                                       start_date, end_date, limit, offset, previous_revision)

    @app.get("/api/v1/agent-review")
    async def agent_review(
        bank: Annotated[str, Query(max_length=100)] = "",
        limit: Annotated[int, Query(ge=1, le=25)] = 10,
        previous_revision: Annotated[str, Query(pattern=r"^(?:[0-9a-f]{64})?$", max_length=64)] = "",
    ) -> dict[str, Any]:
        """Seiche funding, LiquiLens bank research and Undertow liquidity; no trade decision."""
        return await asyncio.to_thread(agent_client.review, bank, limit, previous_revision)

    # Mount at root last so /mcp keeps the SDK's exact transport path.
    app.mount("/", mcp_app)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6900)
    parser.add_argument(
        "--public-base-url",
        default=None,
        help="Public base URL advertised to OpenBB; the proxy must strip any path prefix.",
    )
    args = parser.parse_args()
    import uvicorn

    base_url = args.public_base_url or os.getenv("FINANCIAL_EVIDENCE_BASE_URL")
    if base_url is None:
        advertised_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
        if ":" in advertised_host:
            advertised_host = f"[{advertised_host}]"
        base_url = f"http://{advertised_host}:{args.port}"
    uvicorn.run(
        create_app(base_url=base_url),
        host=args.host,
        port=args.port,
        limit_concurrency=64,
        backlog=128,
        timeout_keep_alive=5,
        proxy_headers=True,
        forwarded_allow_ips=os.getenv(
            "FINANCIAL_EVIDENCE_TRUSTED_PROXIES", "127.0.0.1"
        ),
    )


if __name__ == "__main__":
    main()
