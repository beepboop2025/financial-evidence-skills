"""Read-only snapshot discovery and recovery when host-local receipts are lost."""

from datetime import datetime
from pathlib import Path
import re

from ops_backup import Restic, repository, restore_stopped
from ops_common import HEX, atomic, bound_identity, decode, runtime_identity, sha, utc


def snapshot_metadata(row, cfg):
    if not isinstance(row, dict) or not HEX.fullmatch(row.get("id", "")):
        raise ValueError("invalid exact snapshot identity")
    tags = row.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("invalid snapshot tags")
    installation = "installation-" + cfg["installation_id"]
    operations = [tag.removeprefix("runtime-operation-") for tag in tags if tag.startswith("runtime-operation-")]
    if (row.get("hostname") != "financial-evidence-runtime" or "runtime-ops-v1" not in tags
            or [tag for tag in tags if tag.startswith("installation-")] != [installation]
            or len(operations) != 1 or not re.fullmatch(r"[0-9a-f]{32}", operations[0])):
        raise ValueError("snapshot does not match the bound installation")
    paths = row.get("paths")
    if not isinstance(paths, list) or len(paths) != 1 or not isinstance(paths[0], str):
        raise ValueError("single research payload required")
    path = Path(paths[0])
    if (not path.is_absolute() or ".." in path.parts or str(path) != paths[0]
            or path.parts[-3:] != ("pending", operations[0], "payload")):
        raise ValueError("unexpected research payload path")
    created = datetime.fromisoformat(row["time"].replace("Z", "+00:00"))
    if created.tzinfo is None:
        raise ValueError("snapshot timestamp must have an offset")
    return {"snapshot_id": row["id"], "operation_id": operations[0], "snapshot_time": row["time"],
            "payload_path": str(path), "installation_id": cfg["installation_id"],
            "repository_id": cfg["repository_id"], "status": "candidate_not_restore_verified"}


def candidates(cfg, *, restic=None):
    runtime_identity(cfg)
    restic = restic or Restic()
    repository(restic, cfg["repository_id"])
    rows = decode(restic("snapshots", "--host", "financial-evidence-runtime", "--tag",
                        "installation-" + cfg["installation_id"]), limit=8_388_608)
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError("snapshot catalog exceeds allowance")
    items = [snapshot_metadata(row, cfg) for row in rows]
    if len({row["snapshot_id"] for row in items}) != len(items):
        raise ValueError("duplicate snapshot identity")
    items.sort(key=lambda row: (datetime.fromisoformat(row["snapshot_time"].replace("Z", "+00:00")), row["snapshot_id"]), reverse=True)
    return {"schema": "financial-evidence.runtime-recovery-candidates.v1", "observed_at": utc(),
            "repository_id": cfg["repository_id"], "installation_id": cfg["installation_id"],
            "snapshots": items, "selection": "operator_must_choose_an_exact_snapshot_id",
            "previous_host_verification": "not_established_by_repository_listing",
            "snapshot_mutations": False, "source_network_calls": 0}


def recover_snapshot(cfg, snapshot_id, target, *, restic=None):
    """Authenticate an explicit snapshot, verify it, then reconstruct its receipt."""
    if not isinstance(snapshot_id, str) or not HEX.fullmatch(snapshot_id):
        raise ValueError("full exact snapshot ID required; latest and prefixes are refused")
    runtime_identity(cfg)
    restic = restic or Restic()
    repository(restic, cfg["repository_id"])
    rows = decode(restic("snapshots", snapshot_id), limit=8_388_608)
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("id") != snapshot_id:
        raise ValueError("exact snapshot not uniquely resolved")
    selected = snapshot_metadata(rows[0], cfg)
    manifest_raw = restic("dump", snapshot_id, selected["payload_path"] + "/manifest.json")
    manifest = decode(manifest_raw, limit=65536)
    if (not isinstance(manifest, dict) or set(manifest) != {"schema", "created_at", "operation_id", "package_version",
            "implementation_sha256", "database_sha256", "journal"}
            or manifest["schema"] != "financial-evidence.runtime-offsite-payload.v1"
            or manifest["operation_id"] != selected["operation_id"]
            or manifest["package_version"] != cfg["package_version"]
            or manifest["implementation_sha256"] != cfg["implementation_sha256"]
            or not HEX.fullmatch(manifest["database_sha256"])):
        raise ValueError("snapshot manifest identity differs")
    created = datetime.fromisoformat(manifest["created_at"])
    if created.tzinfo is None:
        raise ValueError("manifest timestamp must have an offset")
    bound_identity(manifest["journal"], cfg)
    expected = {**selected, "manifest_sha256": sha(manifest_raw), "started_at": manifest["created_at"],
                "keys_sha256": manifest["journal"]["keys_sha256"]}
    report = restore_stopped(cfg, expected, target, restic=restic,
                             selection="explicit_snapshot_after_host_receipt_loss")
    # Only the completed full restoration establishes verification. Listing and
    # dumping a manifest never claim that the previous host verified the backup.
    receipt = {"schema": "financial-evidence.runtime-offsite-receipt.v1", "status": "verified",
               **{key: expected[key] for key in ("operation_id", "snapshot_id", "payload_path", "manifest_sha256",
                   "installation_id", "repository_id", "started_at", "keys_sha256")},
               "verified_at": report["restored_at"], "database_sha256": manifest["database_sha256"],
               "runs": manifest["journal"]["runs"], "verified_receipts": report["restored_receipts"],
               "event_cursor": manifest["journal"]["event_cursor"], "verification": "exact encrypted snapshot restored after loss of host-local receipts",
               "prior_host_verification": "unknown", "source_writes": False, "snapshot_deletion": False,
               "snapshot_mutations": False, "mac_required": False}
    atomic(Path(target) / "reconstructed-receipt.json", receipt)
    return {**report, "reconstructed_receipt": str(Path(target) / "reconstructed-receipt.json"),
            "previous_host_verification": "unknown", "snapshot_mutations": False}
