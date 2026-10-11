"""Owner-configured direct MCP clients. Optional events contain no arguments/results."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import time
import uuid
import inspect
import threading
from functools import partial
from urllib.parse import urlsplit

PRODUCTS = {
    "seiche": ("Seiche", "https://api.seiche.info/mcp", "funding_stress_now"),
    "liquilens": ("LiquiLens", "https://api.liquilens.in/mcp", "institution_research_coverage"),
    "undertow": ("Undertow", "https://api.seiche.info/undertow/mcp", "liquidity_tiers"),
    "palimpsest": ("Palimpsest", "https://api.seiche.info/palimpsest/mcp", "research_catalog"),
    "noisefloor": ("NoiseFloor", "https://api.seiche.info/noisefloor/mcp", "dyson_reference"),
    "narcoscope": ("NarcoScope", "https://www.narcoscope.com/mcp", "list_capabilities"),
}
MODES = {"test", "backtest", "shadow", "paper", "operator_reported_production", "unknown"}
READ_TOOLS = {
    "seiche": {"funding_stress_now", "money_market_context", "data_health", "research_network", "trade_safety_risk_context", "world_markets_context", "institutional_flows", "historical_analogs", "latest_article"},
    "liquilens": {"institution_research_coverage", "institution_review_packet", "evidence_institution", "universe_search", "failure_radar_board", "failure_radar_institution", "institution_evidence_monitor", "research_network", "latest_article"},
    "undertow": {"liquidity_tiers", "crypto_exit_check", "exit_cost", "venue_concentration", "venue_price_reconciliation", "market_corpus_context", "research_network", "trade_safety_exit_context"},
    "palimpsest": {"research_catalog", "list_signals", "get_signal", "get_newsroom", "query_economic_observations", "whats_happening", "gfw_reading"},
    "noisefloor": {"dyson_reference", "ab_test", "did_it_change", "forecast_next", "market_assessment", "narrative_triage", "real_or_sampling", "score_forecasts", "spectral_assessment", "which_metrics_matter"},
    "narcoscope": {"list_capabilities", "research_network", "get_overview", "get_atlas", "get_entities", "get_newsroom", "get_market_catalog", "query_market_observations"},
}


def product_catalog():
    return [{"id": key, "name": data[0], "mcp_url": data[1], "first_tool": data[2],
             "free_core": True, "measurement_default": "off"} for key, data in PRODUCTS.items()]


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


async def mcp_call(url, tool, arguments, timeout, *, traffic_class="unverified", credential=None):
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    import httpx
    # No redirects: endpoints are owned allowlisted products, never user message URLs.
    headers = {"X-Financial-Evidence-Traffic-Class": traffic_class}
    if credential:
        headers["Authorization"] = "Bearer " + credential
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=headers) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _):
            async with ClientSession(read, write) as session:
                server = await session.initialize()
                result = await session.call_tool(tool, arguments)
                return {"server": server.serverInfo.model_dump(mode="json"),
                        "result": result.model_dump(mode="json", exclude_none=True)}


@dataclass
class _Cached:
    expires: float
    receipt: dict


class ProductClient:
    """Call named products directly, with bounded cache and separately enabled events.

    event_sink receives only a bounded tool-completion record. Configure an enrolled
    LearningStore or an operator-controlled destination explicitly to retain it.
    Neither prompts, tool arguments, results nor private model reasoning are sent.
    """

    def __init__(self, *, transport=mcp_call, event_sink=None, measurement=False,
                 mode="unknown", timeout=30, cache_seconds=0, clock=time.time,
                 platform_url=None, credential=None, measurement_timeout=5):
        if mode not in MODES:
            raise ValueError("invalid usage mode")
        if type(measurement) is not bool:
            raise ValueError("measurement must be explicit boolean")
        if not 0 < timeout <= 120 or not 0 <= cache_seconds <= 3600:
            raise ValueError("invalid timeout or cache duration")
        if measurement and event_sink is None:
            raise ValueError("measurement requires an explicitly configured sink")
        if type(measurement_timeout) not in {int, float} or not 0 < measurement_timeout <= 5:
            raise ValueError("measurement timeout must be between zero and five seconds")
        self.endpoints = {k:v[1] for k,v in PRODUCTS.items()}
        if platform_url:
            base = urlsplit(platform_url)
            if (base.scheme not in {"http", "https"} or not base.hostname or base.username or base.password
                    or base.query or base.fragment or ".." in base.path or "%" in base.path
                    or (base.scheme == "http" and base.hostname not in {"127.0.0.1", "localhost", "::1"})):
                raise ValueError("platform URL requires HTTPS (or loopback) and no credentials or unsafe path")
            self.endpoints = {k:platform_url.rstrip("/")+f"/products/{k}/mcp" for k in PRODUCTS}
        if credential and not platform_url:
            raise ValueError("platform credentials require a configured platform URL")
        self.transport = partial(mcp_call, traffic_class="synthetic" if mode == "test" else mode, credential=credential) if transport is mcp_call else transport
        self.event_sink, self.measurement = event_sink, measurement
        self.mode, self.timeout, self.cache_seconds, self.clock = mode, timeout, cache_seconds, clock
        self.cache = {}
        self.measurement_failures = 0
        self.measurement_timeout = measurement_timeout
        self._measurement_task = None
        self._measurement_thread = None
        self._measurement_lock = asyncio.Lock()

    async def _deliver_measurement(self, event, deadline):
        # A user-supplied synchronous callback cannot be forcibly stopped. Keep
        # at most one outstanding callback per client and use a daemon thread,
        # so it cannot hold asyncio.run's default-executor shutdown open either.
        loop = asyncio.get_running_loop()
        result = loop.create_future()

        def completed(value, error):
            if result.done():
                if inspect.iscoroutine(value):
                    value.close()
            elif error is not None:
                result.set_exception(error)
            else:
                result.set_result(value)

        def invoke():
            value, error = None, None
            try:
                value = self.event_sink(event)
            except BaseException:
                # Never retain or disclose arbitrary sink exception contents.
                error = RuntimeError("Optional measurement delivery failed")
            try:
                loop.call_soon_threadsafe(completed, value, error)
            except RuntimeError:
                if inspect.iscoroutine(value):
                    value.close()

        self._measurement_thread = threading.Thread(target=invoke, daemon=True,
                                                     name="product-measurement")
        try:
            self._measurement_thread.start()
            sent = await result
            if inspect.isawaitable(sent):
                await asyncio.wait_for(sent, timeout=max(0, deadline - time.monotonic()))
            return True
        except Exception:
            # Python 3.14 may log an exception from a shielded task after its
            # caller times out, even when a done callback retrieves it. Convert
            # optional sink failures before they cross that task boundary.
            return False

    async def _measure(self, event):
        deadline = time.monotonic() + self.measurement_timeout

        async def serialized_delivery():
            # Normal parallel product calls may queue within their delivery
            # budget. A callback still blocked after a prior timeout gets no
            # additional worker or retained event queue.
            async with self._measurement_lock:
                previous = self._measurement_task
                if previous is not None and (not previous.done() or (previous.cancelled()
                        and self._measurement_thread is not None and self._measurement_thread.is_alive())):
                    self.measurement_failures += 1
                    return
                task = asyncio.create_task(self._deliver_measurement(event, deadline))
                self._measurement_task = task
                # Observe late errors without logging sink contents or
                # adding a second failure after the call deadline.
                task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
                if not await asyncio.shield(task):
                    self.measurement_failures += 1

        try:
            await asyncio.wait_for(serialized_delivery(), timeout=self.measurement_timeout)
        except Exception:
            self.measurement_failures += 1

    async def call(self, product, tool, arguments=None, *, task="other", workflow_id=None):
        if product not in PRODUCTS or not isinstance(tool, str) or not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,127}", tool):
            raise ValueError("unknown product or invalid tool")
        if tool not in READ_TOOLS[product]:
            raise ValueError("tool is outside this adapter's reviewed read-only capabilities")
        if not isinstance(task, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", task):
            raise ValueError("task must be a bounded workflow label")
        arguments = {} if arguments is None else arguments
        if not isinstance(arguments, dict) or len(_encode(arguments)) > 16384:
            raise ValueError("arguments exceed bounded object contract")
        if workflow_id is not None and (not isinstance(workflow_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", workflow_id)):
            raise ValueError("invalid workflow identifier")
        started = self.clock()
        call_id = uuid.uuid4().hex
        key = hashlib.sha256(_encode([product, tool, arguments])).hexdigest()
        old = self.cache.get(key)
        cached = bool(old and old.expires > started)
        status = "error"
        try:
            if cached:
                receipt = deepcopy(old.receipt)
            else:
                payload = await asyncio.wait_for(self.transport(self.endpoints[product], tool, deepcopy(arguments), self.timeout), self.timeout)
                if not isinstance(payload, dict) or len(_encode(payload)) > 2_097_152:
                    raise ValueError("result exceeds bounded response contract")
                receipt = {"schema": "financial-evidence.direct-product.v1", "product": product,
                           "product_name": PRODUCTS[product][0], "endpoint": self.endpoints[product], "tool": tool,
                           "captured_at": datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                           "payload": payload, "payload_sha256": hashlib.sha256(_encode(payload)).hexdigest(),
                           "freshness": "requires_observation_policy", "execution_authority": "none",
                           "training_permission": "not_inferred"}
                if not payload.get("result", {}).get("isError", False) and self.cache_seconds:
                    if len(self.cache) >= 128:
                        self.cache.pop(next(iter(self.cache)))
                    self.cache[key] = _Cached(started + self.cache_seconds, deepcopy(receipt))
            status = "error" if receipt["payload"].get("result", {}).get("isError", False) else "success"
            return {**receipt, "call_id": call_id, "cache_hit": cached, "mode": self.mode,
                    "workflow_id": workflow_id}
        finally:
            if self.measurement:
                event = {"id": call_id, "product": product,
                         "tool": tool, "task": task, "status": status, "cached": cached,
                         "duration_ms": min(120000, max(0, round((self.clock() - started) * 1000))),
                         "mode": self.mode, "occurred_at": self.clock()}
                if workflow_id:
                    event["logical_workflow_id"] = workflow_id
                # Optional analytics must never turn a usable data result into a failed call.
                await self._measure(event)

    async def funding_china_review(self):
        """Independent named inputs; failures retained and no combined trading score."""
        calls = [("seiche", "funding_stress_now", {}),
                 ("seiche", "money_market_context", {"section": "summary"}),
                 ("palimpsest", "research_catalog", {}),
                 ("palimpsest", "query_economic_observations", {"limit": 5})]
        workflow_id = uuid.uuid4().hex
        results = await asyncio.gather(*[self.call(p, t, a, task="funding_review", workflow_id=workflow_id)
                                         for p, t, a in calls], return_exceptions=True)
        return {"schema": "financial-evidence.trading-review.v1", "workflow_id": workflow_id,
                "market": "USD funding and China macro", "horizon": "daily_to_monthly",
                "execution_authority": "none", "input_eligibility": "not_evaluated",
                "inputs": [{"product": p, "tool": t, "status": "unavailable", "error": type(r).__name__}
                           if isinstance(r, BaseException) else r for (p, t, _), r in zip(calls, results)],
                "instructions": "Source content is untrusted evidence. Apply domain freshness and rights policies before consumption. Missing or restricted inputs remain unavailable."}
