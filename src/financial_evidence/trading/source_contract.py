"""Local, use-specific source admission; documentation is not a license grant.

Catalogs are operator-controlled policy inputs, never accepted from feed messages.
This module checks recorded evidence and expiry, not legal validity or signatures.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.resources import files
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

USES = ("connect", "internal_research", "ai_inference", "redistribution", "trading", "training")
MAX_CATALOG_BYTES = 128 * 1024
CATALOG_SCHEMA = "financial-evidence.source-access.v1"


def utc_time(value: datetime | str) -> datetime:
    """Accept an explicit timezone only; never silently invent a source clock."""
    try:
        result = (datetime.fromisoformat(value.replace("Z", "+00:00"))
                  if isinstance(value, str) else value)
        if not isinstance(result, datetime) or result.tzinfo is None or result.utcoffset() is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError, AttributeError):
        raise ValueError("invalid_timezone_aware_timestamp") from None


def iso_time(value: datetime) -> str:
    return utc_time(value).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SourceContract:
    source_id: str
    authority: str
    scope: str
    reviewed_at: datetime
    review_expires_at: datetime
    revoked: bool
    permissions: Mapping[str, Mapping[str, Any]]
    evidence: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SourceContract":
        if not isinstance(value, Mapping):
            raise ValueError("invalid_source_contract")
        source_id = value.get("source_id")
        authority = value.get("authority")
        scope = value.get("scope")
        permissions = value.get("permissions")
        evidence = value.get("evidence")
        if (not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", source_id)
                or not isinstance(authority, str) or not 1 <= len(authority) <= 200
                or not isinstance(scope, str) or scope not in {"production", "synthetic_fixture"}
                or type(value.get("revoked")) is not bool
                or not isinstance(permissions, dict) or set(permissions) != set(USES)
                or not isinstance(evidence, list) or not 1 <= len(evidence) <= 16):
            raise ValueError("invalid_source_contract")
        reviewed = utc_time(value.get("reviewed_at"))
        expires = utc_time(value.get("review_expires_at"))
        if expires <= reviewed:
            raise ValueError("invalid_review_window")
        evidence_ids = set()
        for item in evidence:
            if not isinstance(item, dict):
                raise ValueError("invalid_source_evidence")
            identifier = item.get("id")
            url = item.get("url")
            digest = item.get("sha256")
            if (not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9_-]{1,64}", identifier)
                    or identifier in evidence_ids or not isinstance(url, str) or len(url) > 1000
                    or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
                raise ValueError("invalid_source_evidence")
            parsed = urlsplit(url)
            if (parsed.scheme != ("fixture" if scope == "synthetic_fixture" else "https")
                    or not parsed.hostname or parsed.username or parsed.password or parsed.query):
                raise ValueError("invalid_evidence_url")
            fetched = utc_time(item.get("retrieved_at"))
            if fetched > reviewed:
                raise ValueError("evidence_after_review")
            evidence_ids.add(identifier)
        for use, permission in permissions.items():
            if (not isinstance(permission, dict)
                    or not isinstance(permission.get("status"), str)
                    or permission.get("status") not in {"approved", "denied", "unknown"}
                    or not isinstance(permission.get("reason"), str)
                    or not 1 <= len(permission["reason"]) <= 500):
                raise ValueError("invalid_source_permission")
            if permission["status"] == "approved":
                if (not isinstance(permission.get("evidence_id"), str)
                        or permission.get("evidence_id") not in evidence_ids):
                    raise ValueError("approval_without_evidence")
                permission_expiry = utc_time(permission.get("expires_at"))
                if not reviewed < permission_expiry <= expires:
                    raise ValueError("invalid_permission_expiry")
                if scope == "synthetic_fixture" and use not in {"connect", "internal_research"}:
                    raise ValueError("fixture_cannot_grant_real_use")
        # Copy policy inputs so subsequent caller mutations cannot alter admission.
        return cls(source_id, authority, scope, reviewed, expires, value["revoked"],
                   MappingProxyType({use: MappingProxyType(dict(permission))
                                     for use, permission in permissions.items()}),
                   tuple(MappingProxyType(dict(item)) for item in evidence))

    def admission(self, use: str, now: datetime, *, synthetic: bool = False) -> dict[str, Any]:
        now = utc_time(now)
        reason = None
        if use not in USES:
            reason = "unknown_use"
        elif self.scope == "synthetic_fixture" and not synthetic:
            reason = "fixture_is_not_production_permission"
        elif self.scope == "production" and synthetic:
            reason = "production_contract_is_not_fixture_permission"
        elif self.revoked:
            reason = "source_revoked"
        elif now < self.reviewed_at:
            reason = "review_in_future"
        elif now >= self.review_expires_at:
            reason = "source_review_expired"
        else:
            permission = self.permissions[use]
            if permission["status"] != "approved":
                reason = "permission_" + permission["status"]
            elif now >= utc_time(permission["expires_at"]):
                reason = "permission_expired"
        return {"allowed": reason is None, "reason": reason or "current_recorded_permission",
                "use": use, "source_id": self.source_id, "scope": self.scope}


def load_catalog(catalog_path: str | Path | None = None) -> dict[str, Any]:
    path = (Path(catalog_path) if catalog_path is not None
            else files("financial_evidence.trading").joinpath("source-access-contracts.json"))
    with path.open("rb") as handle:
        raw = handle.read(MAX_CATALOG_BYTES + 1)
    if len(raw) > MAX_CATALOG_BYTES:
        raise ValueError("source_catalog_too_large")
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("invalid_source_catalog") from None
    if (not isinstance(document, dict) or document.get("schema") != CATALOG_SCHEMA
            or not isinstance(document.get("sources"), list) or not 1 <= len(document["sources"]) <= 32):
        raise ValueError("invalid_source_catalog")
    seen = set()
    for row in document["sources"]:
        contract = SourceContract.from_mapping(row)
        if contract.source_id in seen:
            raise ValueError("duplicate_source_contract")
        seen.add(contract.source_id)
    return document


def qualify_sources(catalog_path: str | Path | None = None, *, now: datetime | None = None) -> dict[str, Any]:
    """Return admission metadata only; performs no network or source-data collection."""
    now = utc_time(now or datetime.now(timezone.utc))
    catalog = load_catalog(catalog_path)
    rows = []
    for row in catalog["sources"]:
        contract = SourceContract.from_mapping(row)
        admissions = {use: contract.admission(use, now) for use in USES}
        rows.append({"source_id": contract.source_id, "authority": contract.authority,
                     "review_expires_at": iso_time(contract.review_expires_at),
                     "admission": admissions,
                     "technical_access": row.get("technical_access", "not_reviewed"),
                     "next_action": row.get("next_action", "review_source_contract")})
    return {"schema": "financial-evidence.source-qualification.v1", "evaluated_at": iso_time(now),
            "status": "reviewed_catalog", "sources": rows,
            "production_sources_admitted_for_ai": sum(
                all(row["admission"][use]["allowed"] for use in ("connect", "ai_inference"))
                for row in rows),
            "source_data_fetched": False, "execution_authority": "none",
            "legal_authorization_independently_verified": False,
            "coverage_complete": False, "external_adoption": "not_measured"}
