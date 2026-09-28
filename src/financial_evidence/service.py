"""Shared bounded source cache for concurrent OpenBB, REST and MCP callers."""

from __future__ import annotations

import copy
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from .core import (
    ABSENCE_POLICY,
    CARRIER_VERIFICATION,
    DATA_HANDLING,
    EVIDENCE_STATUS,
    PACKET_SCHEMA,
    ROUTES,
    fetch_source,
    normalize_topics,
)
from .tables import DATASETS, query_packet, validate_query


class EvidenceService:
    """At most six source keys and four network workers, shared across filters.

    Concurrent callers reuse the same in-flight retrieval. Cache age is explicit
    and never changes a source's observation or retrieval timestamps. Failures
    expire quickly; an expired success is never substituted after a failure.
    """

    def __init__(
        self,
        *,
        ttl: float = 60,
        error_ttl: float = 5,
        fetcher: Callable = fetch_source,
        clock: Callable = time.monotonic,
    ):
        if not 0 <= ttl <= 300 or not 0 <= error_ttl <= 30:
            raise ValueError("ttl must be 0..300 and error_ttl 0..30 seconds")
        self.ttl = ttl
        self.error_ttl = error_ttl
        self._fetcher = fetcher
        self._clock = clock
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="evidence")
        self._cache: dict[str, Future] = {}
        self._closed = False

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self._pool.shutdown(wait=True)

    def _load(self, source):
        value = self._fetcher(source, max_bytes=1_048_576, timeout=10)
        return value, self._clock()

    def packet(self, topics) -> dict:
        selected = normalize_topics(topics)
        pending = []
        with self._lock:
            if self._closed:
                raise RuntimeError("Evidence service is closed")
            for topic in selected:
                for source in ROUTES[topic]:
                    future = self._cache.get(source.url)
                    if future is not None and future.done():
                        if future.exception() is not None:
                            future = None
                        else:
                            result, finished = future.result()
                            ttl = self.ttl if result.get("ok") else self.error_ttl
                            if self._clock() - finished >= ttl:
                                future = None
                    hit = future is not None
                    if future is None:
                        future = self._pool.submit(self._load, source)
                        self._cache[source.url] = future
                    pending.append((topic, future, hit))
        results = []
        for topic, future, hit in pending:
            value, finished = future.result()
            results.append(
                {
                    "topic": topic,
                    **copy.deepcopy(value),
                    "cache": {
                        "hit": hit,
                        "age_seconds": round(max(0, self._clock() - finished), 3),
                        "ttl_seconds": self.ttl if value.get("ok") else self.error_ttl,
                    },
                }
            )
        succeeded = sum(bool(row["ok"]) for row in results)
        status = (
            "complete"
            if succeeded == len(results)
            else "partial"
            if succeeded
            else "unavailable"
        )
        return {
            "schema": PACKET_SCHEMA,
            "status": status,
            "transport_status": status,
            "status_semantics": "transport_only",
            "evidence_status": EVIDENCE_STATUS,
            "carrier_verification": CARRIER_VERIFICATION,
            "absence_policy": ABSENCE_POLICY,
            "data_handling": DATA_HANDLING,
            "topics": selected,
            "sources": results,
        }

    def query(
        self,
        dataset: str,
        *,
        entity: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        validate_query(dataset, entity, start_date, end_date, limit, offset)
        return query_packet(
            self.packet(DATASETS[dataset]["topics"]),
            dataset,
            entity=entity,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
