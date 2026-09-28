"""OpenBB router extension loaded only inside an OpenBB environment."""

# OpenBB's code generator needs evaluated type objects to import aliases and models.

import asyncio
import atexit
from functools import lru_cache
from typing import Any

from openbb_core.app.model.obbject import OBBject
from openbb_core.app.router import Router

from .core import ROUTES, build_packet, normalize_topics, route_manifest
from .models import EvidenceRow
from .service import EvidenceService
from .tables import Dataset, dataset_catalog


router = Router(
    prefix="",
    description=(
        "Read-only routes to public LiquiLens, Undertow, Seiche, and "
        "Palimpsest evidence."
    ),
)


def _split_topics(topics: str | None, *, default_all: bool = False) -> list[str]:
    if topics:
        return normalize_topics([topics])
    if default_all:
        return list(ROUTES)
    raise ValueError("topics is required")


@router.command(methods=["GET"], no_validate=True)
async def routes(topics: str | None = None) -> OBBject[dict[str, Any]]:
    """Resolve comma-separated research topics to fixed public evidence routes."""

    selected = _split_topics(topics, default_all=True)
    return OBBject(results=route_manifest(selected))


@router.command(methods=["GET"], no_validate=True)
async def fetch(
    topics: str,
    max_bytes: int = 1_048_576,
    timeout: float = 10.0,
) -> OBBject[dict[str, Any]]:
    """Fetch a bounded public evidence packet for comma-separated topics."""

    if not 1 <= max_bytes <= 4_194_304:
        raise ValueError("max_bytes must be between 1 and 4194304")
    if not 0 < timeout <= 30:
        raise ValueError("timeout must be greater than 0 and at most 30")
    selected = _split_topics(topics)
    packet = await asyncio.to_thread(
        build_packet,
        selected,
        max_bytes=max_bytes,
        timeout=timeout,
    )
    return OBBject(results=packet)


@lru_cache(maxsize=1)
def _service() -> EvidenceService:
    service = EvidenceService()
    atexit.register(service.close)
    return service


@router.command(methods=["GET"], no_validate=True)
async def datasets() -> OBBject[list[dict[str, Any]]]:
    """Discover seven tabular financial datasets, their filters and boundaries."""
    return OBBject(results=dataset_catalog())


@router.command(methods=["GET"], no_validate=True)
async def query(
    dataset: Dataset,
    entity: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> OBBject[list[EvidenceRow]]:
    """Get cited financial rows ready for to_df(), with bounded pagination.

    Filter entity IDs or names by a case-insensitive substring. Dates use
    YYYY-MM-DD and refer to observation dates, never retrieval time. Null values
    remain missing or withheld. Inspect extra.metadata for source errors,
    publisher clocks, cache age, total_rows and next_offset.
    """
    result = await asyncio.to_thread(
        _service().query,
        dataset,
        entity=entity or None,
        start_date=start_date or None,
        end_date=end_date or None,
        limit=limit,
        offset=offset,
    )
    return OBBject(
        results=[EvidenceRow(**row) for row in result["results"]],
        extra={
            "metadata": {
                key: value for key, value in result.items() if key != "results"
            }
        },
    )


@router.command(methods=["GET"], no_validate=True)
async def sources() -> OBBject[list[EvidenceRow]]:
    """Audit all public source transports, hashes and reported clocks."""
    return await query(dataset="source_health")
