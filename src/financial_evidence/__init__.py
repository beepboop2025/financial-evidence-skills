"""Public financial-evidence routing package."""

from .core import (
    ALIASES,
    ROUTES,
    SOURCE_ADAPTERS,
    Source,
    build_packet,
    fetch_source,
    normalize_topics,
    source_reported_metadata,
)

__all__ = [
    "ALIASES",
    "ROUTES",
    "SOURCE_ADAPTERS",
    "Source",
    "build_packet",
    "fetch_source",
    "normalize_topics",
    "source_reported_metadata",
]
__version__ = "0.1.5"
