"""Stable versioned views of the existing verified forward packet archive."""

from . import institutional as store
from .reliability import strict_json

SCHEMA = "financial-evidence.funding.v1"


def current(root):
    state = store.latest(root)
    if not state["available"] or not state["ready"]:
        raise ValueError("funding evidence is unavailable, stale, or not ready")
    manifest, raw, _ = store.packet(root, state["packet"]["packet_id"])
    review = strict_json(raw)
    if manifest["ready_at_capture"] is not True or review["ready"] is not True:
        raise ValueError("funding packet was not ready at capture")
    identifier = manifest["packet_id"]
    return {
        "schema": SCHEMA,
        "dataset": "usd-funding",
        "ready": True,
        "packet_id": identifier,
        "source_captured_at": manifest["source_captured_at"],
        "archived_at": manifest["archived_at"],
        "review_asof": manifest["review_asof"],
        "review_scope": manifest["review_scope"],
        "latest_per_instrument": False,
        "value_basis": manifest["value_basis"],
        "knowledge_time_basis": manifest["knowledge_time_basis"],
        "observations": review["results"],
        "manifest_sha256": store.digest(store.encoded(manifest)),
        "artifacts": manifest["artifacts"],
        "links": {
            name: "/packets/" + identifier + "/" + name
            for name in ("manifest.json", "review.json", "observations.csv")
        },
    }


def changes(root, since, latest):
    value = store.compare(root, since, latest["packet_id"])
    return dict(
        value,
        schema="financial-evidence.funding-changes.v1",
        ready=True,
        packet_id=latest["packet_id"],
        review_asof=latest["review_asof"],
    )
