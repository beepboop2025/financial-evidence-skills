import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "funding_offsite", SCRIPTS / "offsite_funding_review.py"
)
offsite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offsite)
REPOSITORY = "a" * 64
SNAPSHOT = "b" * 64


def fixture(root):
    folder = root / "captures/example-1"
    folder.mkdir(parents=True)
    raw = b'{"ready":false}'
    (folder / "review.json").write_bytes(raw)
    manifest = offsite.encoded(
        {"artifact_sha256": {"review.json": hashlib.sha256(raw).hexdigest()}}
    )
    (folder / "manifest.json").write_bytes(manifest)
    (root / "current.json").write_bytes(
        offsite.encoded(
            {
                "latest": {
                    "capture": "captures/example-1",
                    "capture_id": "example-1",
                    "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
                }
            }
        )
    )
    return folder


class OffsiteTests(unittest.TestCase):
    def test_interrupted_compressed_work_reclaims_only_the_recorded_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state, scratch = root / "state", root / "scratch"
            state.mkdir()
            scratch.mkdir()
            old = scratch / (".verified-backup-" + "a" * 32)
            old.mkdir(mode=0o700)
            (old / "interrupted-file").write_text("partial")
            separate = scratch / "retained"
            separate.write_text("unrelated")
            marker = state / ".scratch-attempt.json"
            record = {"scratch": str(scratch), "name": old.name, "repository_id": REPOSITORY}
            marker.write_text(json.dumps(record))
            with offsite.working_directory(state, scratch, REPOSITORY) as work:
                self.assertFalse(old.exists())
                self.assertTrue(work.is_dir())
                self.assertEqual(work.parent, scratch)
                self.assertEqual(json.loads(marker.read_bytes())["name"], work.name)
            self.assertFalse(work.exists())
            self.assertFalse(marker.exists())
            self.assertEqual(separate.read_text(), "unrelated")

    def test_scratch_cleanup_rejects_changed_repository_or_redirected_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state, scratch = root / "state", root / "scratch"
            state.mkdir()
            scratch.mkdir()
            marker = state / ".scratch-attempt.json"
            for name, repo in (("../retained", REPOSITORY), (".verified-backup-" + "a" * 32, "b" * 64)):
                with self.subTest(name=name, repo=repo):
                    marker.write_text(json.dumps({"scratch": str(scratch), "name": name, "repository_id": repo}))
                    with self.assertRaisesRegex(ValueError, "unrecognized"):
                        with offsite.working_directory(state, scratch, REPOSITORY):
                            self.fail("overlapping scratch was admitted")
                    self.assertTrue(marker.exists())
            marker.unlink()
            marker.symlink_to(scratch)
            with self.assertRaises(OSError):
                offsite.clear_recorded_work(state, scratch, REPOSITORY)

    def test_cli_distinguishes_storage_deferral_from_failure_in_an_optional_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = root / "offsite_funding_review.py"
            shutil.copyfile(SCRIPTS / entry.name, entry)
            shutil.copyfile(SCRIPTS / "backup_funding_review.py", root / "backup_funding_review.py")
            cmd = [
                sys.executable, "-B", str(entry), "--source", str(root / "source"),
                "--state", str(root / "state"), "--repository-id", "invalid",
            ]
            env = {"PATH": os.environ["PATH"]}
            standalone = subprocess.run(cmd, env=env, capture_output=True)
            self.assertEqual(standalone.returncode, 1)
            self.assertEqual(json.loads(standalone.stdout)["error_type"], "ValueError")
            (root / "funding_offsite_admission.py").write_text(
                "from contextlib import contextmanager\n"
                "class StorageBusy(Exception): pass\n"
                "@contextmanager\n"
                "def storage_admission(source, state, policy):\n"
                "    assert source.parent == state.parent == policy.parent\n"
                "    if policy.name == 'busy': raise StorageBusy()\n"
                "    if policy.name == 'invalid': raise PermissionError()\n"
                "    yield\n"
            )
            for policy, code, expected in (
                ("busy", 75, {"status": "deferred", "reason": "native_storage_busy",
                              "execution_started": False}),
                ("invalid", 1, {"status": "failed", "error_type": "PermissionError"}),
                ("admitted", 1, {"status": "failed", "error_type": "ValueError"}),
            ):
                with self.subTest(policy=policy):
                    run = subprocess.run(
                        cmd, env={**env, "FUNDING_OFFSITE_STORAGE_POLICY": str(root / policy)},
                        capture_output=True,
                    )
                    self.assertEqual(run.returncode, code)
                    self.assertEqual(json.loads(run.stdout), expected)
                    self.assertFalse((root / "state").exists())

    def test_atlas_capture_bound_applies_to_staging_and_exact_restore(self):
        for name, size, accepted in (
            ("atlas.response", 4 * 1024 * 1024 + 1, True),
            ("atlas.response", 4 * 1024 * 1024 + 2, False),
            ("health.response", 2 * 1024 * 1024 + 2, False),
        ):
            with self.subTest(name=name, size=size), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                folder = fixture(root / "source")
                raw = b"x" * size
                (folder / name).write_bytes(raw)
                manifest = json.loads((folder / "manifest.json").read_bytes())
                manifest["artifact_sha256"][name] = hashlib.sha256(raw).hexdigest()
                manifest_raw = offsite.encoded(manifest)
                (folder / "manifest.json").write_bytes(manifest_raw)
                current = json.loads((root / "source/current.json").read_bytes())
                current["latest"]["manifest_sha256"] = hashlib.sha256(manifest_raw).hexdigest()
                (root / "source/current.json").write_bytes(offsite.encoded(current))
                stage = root / "stage"
                stage.mkdir()
                if accepted:
                    result = offsite.stage_archive(root / "source", stage)
                    self.assertEqual(result["files"]["captures/example-1/" + name], hashlib.sha256(raw).hexdigest())
                    offsite.verify_restore(stage, result["files"])
                else:
                    with self.assertRaisesRegex(ValueError, "bounded regular data"):
                        offsite.stage_archive(root / "source", stage)

    def test_stages_only_completed_captures_and_keeps_original_current(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root / "source")
            (root / "source/captures/unfinished").mkdir()
            (root / "source/captures/unfinished/partial.response").write_bytes(
                b"partial"
            )
            stage = root / "stage"
            stage.mkdir()
            result = offsite.stage_archive(root / "source", stage)
            self.assertEqual(result["completed_captures"], 1)
            self.assertEqual(len(result["files"]), 3)
            self.assertFalse((stage / "captures/unfinished").exists())
            self.assertEqual(
                (stage / "current.json").read_bytes(),
                (root / "source/current.json").read_bytes(),
            )
            offsite.verify_restore(stage, result["files"])

    def test_corrupted_capture_is_rejected_before_upload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = fixture(root / "source")
            (folder / "review.json").write_bytes(b"changed")
            with patch.object(
                offsite, "restic", return_value=offsite.encoded({"id": REPOSITORY})
            ) as run:
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    offsite.backup(root / "source", root / "state", REPOSITORY)
            self.assertEqual(
                [call.args for call in run.call_args_list], [("cat", "config")]
            )
            self.assertEqual(
                json.loads((root / "state/status.json").read_bytes())["status"],
                "failed",
            )

    def test_current_reference_must_exist_in_completed_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root / "source")
            current = json.loads((root / "source/current.json").read_bytes())
            current["latest"]["manifest_sha256"] = "0" * 64
            (root / "source/current.json").write_bytes(offsite.encoded(current))
            (root / "stage").mkdir()
            with self.assertRaisesRegex(ValueError, "current references"):
                offsite.stage_archive(root / "source", root / "stage")

    def test_symlink_at_any_relative_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = fixture(root / "source")
            (root / "linked-directory").symlink_to(folder, target_is_directory=True)
            (root / "linked-file").symlink_to(folder / "review.json")
            for relative in ("linked-directory/review.json", "linked-file"):
                with self.subTest(relative=relative), self.assertRaises(OSError):
                    offsite.read_file(root, relative, 100)

    def test_repository_identity_failure_performs_no_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture(root / "source")
            with patch.object(
                offsite, "restic", return_value=offsite.encoded({"id": "c" * 64})
            ) as run:
                with self.assertRaisesRegex(ValueError, "repository identity"):
                    offsite.backup(root / "source", root / "state", REPOSITORY)
            self.assertEqual(run.call_count, 1)

    def test_only_exact_successful_restore_advances_success_receipt(self):
        for corrupt in (False, True):
            with (
                self.subTest(corrupt=corrupt),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                fixture(root / "source")
                source_before = (root / "source/current.json").read_bytes()
                staged = []

                def run(*arguments):
                    if arguments == ("cat", "config"):
                        return offsite.encoded({"id": REPOSITORY})
                    if arguments[0] == "backup":
                        staged.append(Path(arguments[-1]))
                        shutil.copytree(staged[0], root / "snapshot")
                        return (
                            json.dumps(
                                {"message_type": "summary", "snapshot_id": SNAPSHOT}
                            )
                            + "\n"
                        ).encode()
                    self.assertEqual(arguments[:3], ("restore", SNAPSHOT, "--target"))
                    self.assertFalse(staged[0].exists())
                    restored = Path(arguments[3])
                    self.assertEqual(list(restored.iterdir()), [])
                    destination = restored / staged[0].relative_to("/")
                    shutil.copytree(root / "snapshot", destination)
                    if corrupt:
                        (destination / "captures/example-1/review.json").write_bytes(
                            b"bad"
                        )
                    return b"{}\n"

                with patch.object(offsite, "restic", side_effect=run):
                    if corrupt:
                        with self.assertRaisesRegex(ValueError, "restored artifact"):
                            offsite.backup(root / "source", root / "state", REPOSITORY)
                    else:
                        receipt = offsite.backup(
                            root / "source", root / "state", REPOSITORY
                        )
                        self.assertEqual(receipt["snapshot_id"], SNAPSHOT)
                        self.assertEqual(receipt["verified_files"], 3)
                        self.assertFalse(receipt["mac_required"])
                status = json.loads((root / "state/status.json").read_bytes())
                self.assertEqual(status["status"], "failed" if corrupt else "pass")
                self.assertEqual(
                    len(list((root / "state/receipts").glob("*.json"))),
                    0 if corrupt else 1,
                )
                self.assertEqual(
                    (root / "source/current.json").read_bytes(), source_before
                )

    def test_missing_or_ambiguous_snapshot_never_starts_restore(self):
        summary = json.dumps(
            {"message_type": "summary", "snapshot_id": SNAPSHOT}
        ).encode()
        for output in (
            b"",
            summary + b"\n" + summary,
            summary.replace(SNAPSHOT.encode(), b"invalid"),
        ):
            with self.subTest(output=output), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture(root / "source")
                with patch.object(
                    offsite,
                    "restic",
                    side_effect=[offsite.encoded({"id": REPOSITORY}), output],
                ) as run:
                    with self.assertRaisesRegex(ValueError, "snapshot identity"):
                        offsite.backup(root / "source", root / "state", REPOSITORY)
                self.assertEqual(
                    [call.args[0] for call in run.call_args_list], ["cat", "backup"]
                )
                status = json.loads((root / "state/status.json").read_bytes())
                self.assertEqual(status["status"], "failed")
                self.assertFalse((root / "state/receipts").exists())

    def test_restore_rejects_added_or_missing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "unexpected").write_bytes(b"unexpected")
            with self.assertRaisesRegex(ValueError, "inventory"):
                offsite.verify_restore(root, {})
            (root / "unexpected").unlink()
            with self.assertRaisesRegex(ValueError, "inventory"):
                offsite.verify_restore(root, {"missing": "0" * 64})


if __name__ == "__main__":
    unittest.main()
