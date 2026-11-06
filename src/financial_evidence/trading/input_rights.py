"""Defence in depth for named, unqualified upstream data in native MCP results.

This is a deny gate, not a source licence or comprehensive source discovery.
The product must still qualify its inputs. Because a mixed document may contain
unlabelled derived totals or prose, one restricted input withholds the entire
result; removing only its leaf would leave recoverable dependent information.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
from urllib.parse import urlparse

POLICY = "financial-evidence.native-input-rights.2026-11-06"
PROVENANCE_KEYS = frozenset({"source", "sources", "source_id", "source_ids", "source_url",
    "source_registry_ids", "provider", "venue", "upstream", "url", "permalink"})
TERMS = {
    "coinbase": "https://www.coinbase.com/legal/market_data",
    "fred": "https://fred.stlouisfed.org/legal/terms/",
    "binance_vision": "https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md",
    "ooni": "https://github.com/ooni/license/blob/master/data/LICENSE.md",
    "telegram": "https://telegram.org/tos/content-licensing",
    "yahoo_finance": "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
    "open_meteo_free_hosted": "https://open-meteo.com/en/terms",
}


def _source_ids(value):
    if isinstance(value, str):
        text = value.lower()
        words = set(re.split(r"[^a-z0-9]+", text))
        host = (urlparse(text).hostname or "").lower()
        if "fred" in words or host == "fred.stlouisfed.org":
            yield "fred"
        if "coinbase" in words:
            yield "coinbase"
        if "data.binance.vision" in text or {"binance", "vision"} <= words:
            yield "binance_vision"
        if "ooni" in words:
            yield "ooni"
        if "telegram" in words or host in {"t.me", "www.t.me", "telegram.org"}:
            yield "telegram"
        if "yahoo" in words:
            yield "yahoo_finance"
        if host in {"archive-api.open-meteo.com", "api.open-meteo.com"}:
            yield "open_meteo_free_hosted"
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _source_ids(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _source_ids(key)
            yield from _source_ids(item)


def restricted_sources(document):
    found = set()
    stack = [document]
    seen = set()
    while stack:
        node = stack.pop()
        if isinstance(node, (dict, list)):
            if id(node) in seen:
                continue
            seen.add(id(node))
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() == "coinbase" and isinstance(value, (dict, list, int, float)):
                    found.add("coinbase")
                if key in PROVENANCE_KEYS:
                    found.update(_source_ids(value))
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return sorted(found)


_PROVENANCE_LINE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?(?:source|sources|source_id|source_url|provider|venue)(?:\*\*)?\s*[:=]\s*(?:\*\*)?([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)


def _text_provenance(text):
    """Only explicit provenance labels; incidental provider mentions do not qualify."""
    if not isinstance(text, str):
        return []
    if len(text) > 2_097_152:
        raise ValueError("native text exceeds bounded rights inspection")
    values = [match.group(1) for match in _PROVENANCE_LINE.finditer(text)]
    if any(len(value) > 2048 for value in values):
        raise ValueError("explicit source provenance exceeds bounded inspection")
    return [{"source": value} for value in values]


def project_native_payload(payload):
    """Project structured and JSON-text MCP representations consistently.

    Unqualified download-time rights are not revoked: archives remain intact,
    but a response without a reviewed content-bound grant is not admitted to AI.
    No user argument, mode flag, or provider self-assertion is a licence override.
    """
    result = payload.get("result")
    if not isinstance(result, dict):
        return payload, None
    documents = [result]
    for block in result.get("content", []):
        if not isinstance(block, dict):
            continue
        resource = block.get("resource")
        if block.get("type") == "resource" and isinstance(resource, dict):
            documents.append({"source_url": resource.get("uri")})
        text = block.get("text") if block.get("type") == "text" else (resource.get("text") if block.get("type") == "resource" and isinstance(resource, dict) else None)
        if text is not None:
            try:
                documents.append(json.loads(text))
            except (ValueError, TypeError):
                documents.extend(_text_provenance(text))
    sources = sorted({source for document in documents for source in restricted_sources(document)})
    if not sources:
        return payload, None
    receipt = {"policy": POLICY, "status": "restricted", "sources": sources,
               "scope": "entire_mixed_result_and_dependents", "ai_inference_eligible": False,
               "redistribution_eligible": False,
               "reason": "Required source-specific AI and external-use qualification is absent from this adapter.",
               "terms": {source: TERMS[source] for source in sources},
               "historical_rights": "Prior-download grants are preserved; no archive is deleted or relicensed. A reviewed download-time grant must be bound to the exact data before admission."}
    safe = {"status": "restricted", "value": None, "source_rights": receipt}
    projected = deepcopy(payload)
    # Replace all result fields, including prose, embedded resources and metadata
    # which may contain the same figures. Keep only a safe MCP result envelope.
    projected["result"] = {"isError": False, "structuredContent": safe,
                           "content": [{"type": "text", "text": json.dumps(safe, sort_keys=True)}]}
    return projected, receipt
