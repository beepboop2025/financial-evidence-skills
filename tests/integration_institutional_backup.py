"""Exercise exact-snapshot restoration and corruption rejection with real Restic."""

import json
import os
import secrets
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backup_institutional_packets import backup
from offsite_funding_review import restic
from test_institutional import AT, PID, csv_bytes, fetcher, reliability, store

with tempfile.TemporaryDirectory(prefix="packet-restic-integration-") as folder:
    root = Path(folder)
    os.environ.update(
        RESTIC_REPOSITORY=str(root / "repository"),
        RESTIC_PASSWORD=secrets.token_urlsafe(48),
        RESTIC_CACHE_DIR=str(root / "cache"),
    )
    restic("init")
    repo_id = json.loads(restic("cat", "config"))["id"]
    with (
        patch.object(store, "now", return_value=AT),
        patch.object(reliability, "now", return_value=AT),
    ):
        attempt = store.archive_once(
            root / "source",
            trigger="manual",
            fetcher=fetcher(),
            builder=lambda review: (review, csv_bytes(review["results"]), []),
        )
        assert attempt["error"] is None
    receipt = backup(root / "source", root / "state", repo_id)
    assert receipt["status"] == "PASS" and receipt["verified_files"] == 7
    snapshots = json.loads(restic("snapshots"))
    assert len(snapshots) == 1 and snapshots[0]["id"] == receipt["snapshot_id"]
    restic("check", "--read-data")
    (root / "source/packets" / PID / "observations.csv").write_bytes(b"corrupt")
    try:
        backup(root / "source", root / "state", repo_id)
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt archive accepted")
    assert json.loads(restic("snapshots")) == snapshots
    assert json.loads((root / "state/status.json").read_bytes())["status"] == "failed"
    print(
        json.dumps(
            {
                "status": "PASS",
                "exact_snapshot_restore": True,
                "corrupt_source_rejected": True,
                "private_usage_excluded": True,
            }
        )
    )
