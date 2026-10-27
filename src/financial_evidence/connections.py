"""Offline, institution-scoped configuration for existing public MCP products.

These are configuration admission checks, not a runtime authorization boundary.
Importing a generated config does not enforce query contents or vendor rights.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import os
from pathlib import Path
import re

from .runtime.contracts import decode, encode, integer
from .trading.client import product_catalog

PROFILE_SCHEMA = "financial-evidence.connection-profile.v1"
MAX_PROFILE_BYTES = 65_536
IDENTIFIER = re.compile(r"[a-z][a-z0-9_-]{0,63}")
REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
CLIENTS = {"mcp": ("mcp.json", "mcpServers"), "vscode": ("vscode.json", "servers")}
BOUNDARY = (
    "Customer-operated configuration for public research only. Profile declarations are not "
    "independent entitlement verification. Client configuration does not enforce tenant isolation, "
    "query filtering, source licences, retention or deletion. No private-data connector, SSO, "
    "regulatory certification, execution authority or third-party subscription access is supplied."
)


def _fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError(f"{label} has missing or unsupported fields")


def _identifier(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase identifier (at most 64 characters)")
    return value


def _reference(value, label):
    if not isinstance(value, str) or not REFERENCE.fullmatch(value):
        raise ValueError(f"{label} must be an identifier, not credentials or free-form content")
    return value


def _list(value, label, limit, *, empty=False):
    if not isinstance(value, list) or not (0 if empty else 1) <= len(value) <= limit:
        raise ValueError(f"{label} must be a list of {'0' if empty else '1'}..{limit} entries")


def connection_catalog():
    """Use the same fixed routes as the shipped product client, without probing them."""
    return {
        "schema": "financial-evidence.connection-catalog.v1",
        "network_access_performed": False,
        "clients": list(CLIENTS),
        "products": product_catalog(),
        "scope": BOUNDARY,
    }


def example_profile():
    """An editable template whose egress remains denied until explicitly approved."""
    institution, workspace = "example-institution", "public-research-demo"
    return {
        "schema": PROFILE_SCHEMA,
        "institution_id": institution,
        "workspace_id": workspace,
        "approval_reference": "REPLACE-WITH-APPROVAL",
        "data_scope": "public_research_only",
        "hosted_queries_approved": False,
        "products": ["financial-evidence"],
        "destinations": [{"client": client, "institution_id": institution, "workspace_id": workspace}
                         for client in CLIENTS],
        "evidence_policy": {"purpose": "internal_research", "source_rights": "check_each_result",
                            "preserve_source_metadata": True, "cross_institution_sharing": False,
                            "retention_days": 90},
        "external_subscriptions": [],
    }


def validate_profile(value, *, today=None):
    """Reject unsupported routes and ambiguous permissions before writing any config."""
    today = datetime.now(timezone.utc).date() if today is None else today
    _fields(value, {"schema", "institution_id", "workspace_id", "approval_reference",
                    "data_scope", "hosted_queries_approved", "products", "destinations",
                    "evidence_policy", "external_subscriptions"}, "profile")
    if value["schema"] != PROFILE_SCHEMA:
        raise ValueError("unsupported connection profile schema")
    institution = _identifier(value["institution_id"], "institution_id")
    workspace = _identifier(value["workspace_id"], "workspace_id")
    _reference(value["approval_reference"], "approval_reference")
    if value["data_scope"] != "public_research_only":
        raise ValueError("these hosted connectors accept public_research_only profiles; private silos need separately qualified infrastructure")
    if value["hosted_queries_approved"] is not True:
        raise ValueError("explicit hosted query egress approval is required")

    admitted = {product["id"] for product in product_catalog()}
    _list(value["products"], "products", len(admitted))
    for product in value["products"]:
        if not isinstance(product, str) or product not in admitted:
            raise ValueError("unknown product route; use connect --catalog")
    if len(set(value["products"])) != len(value["products"]):
        raise ValueError("duplicate products are not allowed")

    _list(value["destinations"], "destinations", len(CLIENTS))
    clients = []
    for destination in value["destinations"]:
        _fields(destination, {"client", "institution_id", "workspace_id"}, "destination")
        if destination["institution_id"] != institution or destination["workspace_id"] != workspace:
            raise ValueError("destination must belong to the same institution and workspace")
        client = destination["client"]
        if not isinstance(client, str) or client not in CLIENTS or client in clients:
            raise ValueError("unknown or duplicate client; supported clients are mcp and vscode")
        clients.append(client)

    policy = value["evidence_policy"]
    _fields(policy, {"purpose", "source_rights", "preserve_source_metadata",
                     "cross_institution_sharing", "retention_days"}, "evidence_policy")
    if policy["purpose"] != "internal_research" or policy["source_rights"] != "check_each_result":
        raise ValueError("internal_research and check_each_result rights review are required")
    if policy["preserve_source_metadata"] is not True or policy["cross_institution_sharing"] is not False:
        raise ValueError("source metadata must be preserved and cross-institution sharing disabled")
    integer(policy["retention_days"], 1, 3650, "retention_days")

    # Subscriptions are declared inventory, never endpoints, credentials or implicit grants.
    subscriptions = value["external_subscriptions"]
    _list(subscriptions, "external_subscriptions", 32, empty=True)
    providers = set()
    for subscription in subscriptions:
        _fields(subscription, {"provider", "entitlement_reference", "rights_status", "expires_on",
                               "dataset_ids", "connection_status"}, "external subscription")
        provider = _identifier(subscription["provider"], "subscription provider")
        if provider in providers:
            raise ValueError("duplicate subscription provider")
        providers.add(provider)
        _reference(subscription["entitlement_reference"], "entitlement_reference")
        if subscription["rights_status"] != "confirmed_internal_research":
            raise ValueError("external subscription rights must be confirmed for internal research")
        if subscription["connection_status"] != "not_connected":
            raise ValueError("external subscriptions are inventory only; their official connectors require separate approval")
        expiry = subscription["expires_on"]
        if not isinstance(expiry, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expiry):
            raise ValueError("subscription expires_on must be YYYY-MM-DD")
        try:
            expires_on = date.fromisoformat(expiry)
        except ValueError:
            raise ValueError("invalid subscription expiry date") from None
        if expires_on < today:
            raise ValueError("external subscription entitlement has expired")
        _list(subscription["dataset_ids"], "dataset_ids", 64)
        for dataset in subscription["dataset_ids"]:
            _reference(dataset, "subscription dataset id")
        if len(set(subscription["dataset_ids"])) != len(subscription["dataset_ids"]):
            raise ValueError("duplicate subscription dataset id")
    raw = encode(value)
    if len(raw) > MAX_PROFILE_BYTES:
        raise ValueError("connection profile exceeds its byte allowance")
    return decode(raw, limit=MAX_PROFILE_BYTES)


def read_profile(path):
    with Path(path).open("rb") as stream:
        return decode(stream.read(MAX_PROFILE_BYTES + 1), limit=MAX_PROFILE_BYTES)


def build_connection_package(value, *, now=None):
    """Return usable configs and a review receipt; never fetch or execute a connector."""
    now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None:
        raise ValueError("package time requires a timezone")
    now = now.astimezone(timezone.utc)
    profile = validate_profile(value, today=now.date())
    catalog = {product["id"]: product for product in product_catalog()}
    products = [catalog[identifier] for identifier in profile["products"]]
    servers = {product["id"]: {"type": "http", "url": product["mcp_url"]} for product in products}
    configs = {}
    for destination in profile["destinations"]:
        filename, root_key = CLIENTS[destination["client"]]
        configs[filename] = {root_key: servers.copy()}
    receipt = {
        "schema": "financial-evidence.connection-receipt.v1",
        "generated_at": now.isoformat(),
        "institution_id": profile["institution_id"],
        "workspace_id": profile["workspace_id"],
        "approval_reference": profile["approval_reference"],
        "profile_sha256": hashlib.sha256(encode(profile)).hexdigest(),
        "config_sha256": {name: hashlib.sha256(encode(config) + b"\n").hexdigest()
                          for name, config in configs.items()},
        "products": products,
        "network_access_performed": False,
        "credentials_collected": False,
        "private_data_connected": False,
        "external_subscriptions_connected": False,
        "runtime_policy_enforced": False,
        "source_rights_verified": False,
        "retention_enforced": False,
        "scope": BOUNDARY,
    }
    return {"profile": profile, "configs": configs, "receipt": receipt}


def _instructions(package):
    profile = package["profile"]
    names = ", ".join(product["name"] for product in package["receipt"]["products"])
    return f"""# Financial Evidence connection package

Institution: `{profile['institution_id']}`. Workspace: `{profile['workspace_id']}`.
Approved product connections: {names}.

This package was generated offline. It contains configuration and declared approval metadata, not financial data or credentials. Importing a config enables subsequent requests to the hosted URLs; review your client's trust/permission prompt first.

- `mcp.json`, when present, uses `mcpServers` for clients supporting remote Streamable HTTP MCP. Merge only these named server entries into the approved client workspace; do not replace an existing configuration blindly. Client account/plan requirements still apply.
- `vscode.json`, when present, uses `servers`. Merge its entries into the approved workspace's `.vscode/mcp.json`, then review VS Code's server trust prompt.
- Use the same approved product IDs on another supported client to retain the connection choices. Keep `profile.json` and `connection-receipt.json` with the handoff. Do not copy this package to another institution or workspace.
- Public research queries only. Do not put private customer records, positions, documents, credentials or licensed third-party data in tool arguments. These client configurations do not enforce that restriction.
- External subscriptions listed in the profile are inventory only. Obtain each vendor's approved connector and verify its access, export, derived-data and redistribution terms separately. No entitlement is transferred by this package.
- Check each result's rights before use or export. Preserve original evidence, source URLs, native units, observation/publication/retrieval dates, gaps and revisions. Unknown or restricted rights are a hold, not permission. A successful connection is not source freshness or regulatory compliance.
- The declared retention target is {profile['evidence_policy']['retention_days']} days. Your institution must implement access control, permitted retention and deletion; this generator does not enforce them.
- For public-evidence reviews use `financial-evidence start` to select an existing workflow. `financial-evidence review funding --selection USD --output reviews` explicitly fetches and saves a result, brief and receipt. No workflow is run by generating or importing this package.

{BOUNDARY}
"""


def write_connection_package(package, output):
    """Create only a new private directory; never merge or replace user configuration."""
    target = Path(output)
    files = {**{name: encode(config) + b"\n" for name, config in package["configs"].items()},
             "profile.json": encode(package["profile"]) + b"\n",
             "connection-receipt.json": encode(package["receipt"]) + b"\n",
             "README.md": _instructions(package).encode("utf-8")}
    # The CLI builds and validates before calling this writer. Never accept an existing path.
    target.mkdir(mode=0o700)
    for name, raw in files.items():
        fd = os.open(target / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return {"directory": str(target), "files": list(files),
            "network_access_performed": False, "scope": BOUNDARY}
