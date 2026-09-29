"""Exercise the installed Restic binary with an isolated encrypted repository."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from test_funding_offsite import fixture, offsite


def main():
    with tempfile.TemporaryDirectory(prefix="funding-restic-integration-") as folder:
        root = Path(folder)
        os.environ.update(
            RESTIC_REPOSITORY=str(root / "repository"),
            RESTIC_PASSWORD=secrets.token_urlsafe(48),
            RESTIC_CACHE_DIR=str(root / "cache"),
        )
        offsite.restic("init")
        repository_id = json.loads(offsite.restic("cat", "config"))["id"]
        fixture(root / "source")
        receipt = offsite.backup(root / "source", root / "state", repository_id)
        assert receipt["status"] == "pass" and receipt["verified_files"] == 3
        snapshots = json.loads(offsite.restic("snapshots"))
        assert len(snapshots) == 1 and snapshots[0]["id"] == receipt["snapshot_id"]
        offsite.restic("check", "--read-data")
        (root / "source/captures/example-1/review.json").write_bytes(b"changed")
        try:
            offsite.backup(root / "source", root / "state", repository_id)
        except ValueError as error:
            assert "hash mismatch" in str(error)
        else:
            raise AssertionError("corrupt source was accepted")
        assert json.loads(offsite.restic("snapshots")) == snapshots
        assert len(list((root / "state/receipts").glob("*.json"))) == 1
        assert (
            json.loads((root / "state/status.json").read_bytes())["status"] == "failed"
        )
        print(
            json.dumps(
                {
                    "status": "pass",
                    "real_restic_restore": True,
                    "full_repository_check": True,
                    "corrupt_source_rejected": True,
                    "restic_version": subprocess.check_output(
                        ["restic", "version"], text=True
                    ).strip(),
                }
            )
        )


if __name__ == "__main__":
    main()
