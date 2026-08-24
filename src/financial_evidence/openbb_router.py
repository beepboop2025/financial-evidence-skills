"""OpenBB router extension loaded only inside an OpenBB environment."""

from __future__ import annotations

import asyncio
from typing import Any

from openbb_core.app.model.obbject import OBBject
from openbb_core.app.router import Router

from .core import ROUTES, build_packet, normalize_topics, route_manifest


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
