import base64
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "funding_backup",
    Path(__file__).resolve().parents[1] / "scripts/backup_funding_review.py",
)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def fixture():
    review = b'{"ready":false}'
    manifest = json.dumps(
        {"artifact_sha256": {"review.json": hashlib.sha256(review).hexdigest()}}
    ).encode()
    capture = {
        "path": "captures/example-1",
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "artifacts": json.loads(manifest)["artifact_sha256"],
    }
    current = {
        "latest": {
            "capture": capture["path"],
            "capture_id": "example-1",
            "manifest_sha256": capture["manifest_sha256"],
        }
    }
    inventory = {
        "captures": [capture],
        "current": base64.b64encode(json.dumps(current).encode()).decode(),
    }
    return inventory, {"manifest.json": manifest, "review.json": review}


class BackupTests(unittest.TestCase):
    def test_backup_limits_follow_capture_policy(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        policy_spec = importlib.util.spec_from_file_location("backup_test_policy", scripts / "check_funding_review.py")
        policy = importlib.util.module_from_spec(policy_spec)
        policy_spec.loader.exec_module(policy)
        self.assertEqual(backup.artifact_limit("atlas.response"), policy.ATLAS_MAX_BYTES + 1)
        self.assertEqual(backup.artifact_limit("health.response"), policy.MAX_BYTES + 1)
        self.assertEqual(backup.artifact_limit("captures/example/atlas.response"), policy.ATLAS_MAX_BYTES + 1)

    def test_pull_hashes_atlas_but_rejects_oversized_other_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw = b"x" * (2 * 1024 * 1024 + 2)
            for name in ("atlas.response", "health.response"):
                path = root / name
                path.write_bytes(raw)
                if name == "atlas.response":
                    self.assertEqual(backup.digest(path, backup.artifact_limit(name)), hashlib.sha256(raw).hexdigest())
                else:
                    with self.assertRaisesRegex(ValueError, "exceeds bound"):
                        backup.digest(path, backup.artifact_limit(name))

    def test_invalid_inventory_is_rejected_before_transfer(self):
        for field, value in [
            ("path", "captures/../../secrets"),
            ("manifest_sha256", "not-a-hash"),
            ("artifacts", {"../secret.json": "a" * 64}),
            ("artifacts", {"review.json": "bad"}),
        ]:
            inventory, _ = fixture()
            inventory["captures"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                backup.validate_inventory(inventory)

    def test_current_must_bind_retained_manifest(self):
        inventory, _ = fixture()
        inventory["captures"][0]["manifest_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            backup.validate_inventory(inventory)

    def test_ssh_option_injection_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(backup.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    backup.backup("-oProxyCommand=bad", Path(folder))
                run.assert_not_called()

    def test_pull_verifies_before_advancing_and_never_replaces_old_evidence(self):
        inventory, files = fixture()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)

            def run(args, **kwargs):
                if args[0] == "ssh":
                    return subprocess.CompletedProcess(
                        args, 0, json.dumps(inventory), ""
                    )
                self.assertIn("--ignore-existing", args)
                target = root / "captures/example-1"
                target.mkdir(parents=True, exist_ok=True)
                for name, raw in files.items():
                    if not (target / name).exists():
                        (target / name).write_bytes(raw)
                return subprocess.CompletedProcess(args, 0)

            with (
                patch.object(backup.subprocess, "run", side_effect=run),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                receipt = backup.backup("host", root)
                self.assertEqual(receipt["verified_files"], 2)
                original_current = (root / "current.json").read_bytes()
                (root / "captures/example-1/review.json").write_bytes(b"corrupted")
                with self.assertRaisesRegex(ValueError, "artifact hash mismatch"):
                    backup.backup("host", root)
                self.assertEqual((root / "current.json").read_bytes(), original_current)
                self.assertEqual(
                    (root / "captures/example-1/review.json").read_bytes(), b"corrupted"
                )
                self.assertEqual(
                    len(list((root / "backup-receipts").glob("*.json"))), 1
                )

    def test_symlinked_artifact_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "raw").write_text("data")
            (root / "link").symlink_to(root / "raw")
            with self.assertRaises(ValueError):
                backup.digest(root / "link", 100)


if __name__ == "__main__":
    unittest.main()
