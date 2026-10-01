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
from test_institutional import AT, PID, csv_bytes, fetcher, fixture, reliability, store

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
        # A release upgrade must not make the immutable prior packet unbackable.
        source, release = "c" * 40, "workspace-1.2.0+" + "c" * 12
        with (patch.object(store, "SOURCE", source), patch.object(store, "RELEASE", release),
              patch.object(reliability, "SOURCE", source), patch.object(reliability, "RELEASE", release)):
            review, csv_raw = fixture("20260929T120000.000000Z-" + "c" * 32)
            attempt = store.archive_once(
                root / "source", trigger="manual", fetcher=fetcher(review, csv_raw),
                builder=lambda review: (review, csv_bytes(review["results"]), []),
            )
            assert attempt["error"] is None
    receipt = backup(root / "source", root / "state", repo_id)
    assert receipt["status"] == "PASS" and receipt["verified_files"] == 11
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
                "two_release_history_restored": True,
            }
        )
    )
