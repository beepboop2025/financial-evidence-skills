"""Contract checks for the optional shared-volume backup admission."""

from contextlib import ExitStack, contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "scripts/funding_offsite_admission.py"
spec = importlib.util.spec_from_file_location("funding_offsite_admission", MODULE)
admission = importlib.util.module_from_spec(spec)
spec.loader.exec_module(admission)


class StorageAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.source = self.base / "source"
        self.state = self.base / "state"
        self.state.mkdir()
        (self.source / "captures" / "complete").mkdir(parents=True)
        (self.source / "current.json").write_bytes(b"a")
        (self.source / "captures/complete/manifest.json").write_bytes(b"b")
        (self.source / "captures/complete/data").write_bytes(b"x" * 4100)
        self.policy = {
            "schema": "financial-evidence.native-storage-admission.v1",
            "helper": "/trusted/helper.py",
            "helper_sha256": "a" * 64,
            "state": str(self.state),
            "mount": str(self.base),
            "filesystem": "ext4",
            "uuid": "test-volume",
            "reserve_bytes": 4 * 1024**2,
        }

    def guard(self, helper):
        self.patches.enter_context(
            mock.patch.object(
                admission, "_root_file", return_value=json.dumps(self.policy).encode()
            )
        )
        self.patches.enter_context(
            mock.patch.object(admission, "_helper", return_value=helper)
        )
        return admission.storage_admission(
            self.source, self.state, self.base / "policy"
        )

    def test_both_locks_cover_capacity_check_and_backup(self):
        calls = []

        @contextmanager
        def locked(*, include_existing_ci, wait_seconds):
            calls.append((include_existing_ci, wait_seconds))
            try:
                yield
            finally:
                calls.append("released")

        check = self.patches.enter_context(
            mock.patch.object(
                admission,
                "_check_reserve",
                side_effect=lambda *a: calls.append("reserve"),
            )
        )
        with self.guard(types.SimpleNamespace(admission=locked)):
            calls.append("backup")
        check.assert_called_once()
        self.assertEqual(calls, [(True, 60), "reserve", "backup", "released"])

    def test_contention_is_distinguished_from_a_changed_or_missing_lock(self):
        @contextmanager
        def locked(**options):
            raise ValueError(reason)
            yield

        for reason, expected in (
            ("Storage admission is held by another job", admission.StorageBusy),
            ("Storage admission lock was replaced", ValueError),
        ):
            with self.subTest(reason=reason), self.assertRaises(expected):
                with self.guard(types.SimpleNamespace(admission=locked)):
                    self.fail("backup started")

    def test_error_after_admission_is_not_deferred(self):
        @contextmanager
        def locked(**options):
            yield

        self.patches.enter_context(mock.patch.object(admission, "_check_reserve"))
        with self.assertRaisesRegex(ValueError, "held by another job"):
            with self.guard(types.SimpleNamespace(admission=locked)):
                raise ValueError("Storage admission is held by another job")

    def test_only_completed_capture_trees_contribute_to_estimate(self):
        before = admission._stage_bytes(self.source, 4096)
        partial = self.source / "captures/incomplete"
        partial.mkdir()
        (partial / "scratch").write_bytes(b"x" * 50_000)
        self.assertEqual(admission._stage_bytes(self.source, 4096), before)
        self.assertGreaterEqual(before, 4102)

    def mount_rows(self):
        device = self.base.stat().st_dev
        physical = {
            "uuid": "test-volume",
            "fstype": "ext4",
            "target": str(self.base),
            "fsroot": "/",
            "maj:min": f"{os.major(device)}:{os.minor(device)}",
        }
        return physical, {**physical, "target": str(self.state), "fsroot": "/state"}

    def test_full_volume_and_systemd_state_bind_preserve_free_space_check(self):
        estimate = admission._stage_bytes(self.source, 4096)
        size = self.policy["reserve_bytes"] + estimate
        fs = types.SimpleNamespace(f_frsize=4096, f_bavail=(size + 4095) // 4096)
        ident = self.patches.enter_context(
            mock.patch.object(admission.subprocess, "check_output")
        )
        self.patches.enter_context(
            mock.patch.object(admission.os, "statvfs", return_value=fs)
        )
        physical, bind = self.mount_rows()
        sibling = {
            **physical,
            "target": str(self.base / "unrelated"),
            "fsroot": "/elsewhere",
        }
        for mounts in ([physical], [bind, sibling, physical]):
            with self.subTest(mounts=mounts):
                ident.return_value = json.dumps({"filesystems": mounts})
                admission._check_reserve(self.source, self.state, self.policy)
        argv = ident.call_args.args[0]
        self.assertIn("--submounts", argv)
        self.assertEqual(argv[argv.index("--target") + 1], str(self.base))
        fs.f_bavail -= 1
        with self.assertRaisesRegex(OSError, "insufficient space"):
            admission._check_reserve(self.source, self.state, self.policy)

    def test_other_bind_sources_and_mount_identities_are_rejected(self):
        physical, bind = self.mount_rows()
        wrong_rows = [
            [bind],
            [physical, physical],
            [physical, bind, bind],
            [{**physical, "uuid": "other"}],
            [{**physical, "fstype": "xfs"}],
            [{**physical, "fsroot": "/other"}],
            [{**physical, "maj:min": "111:222"}],
            [physical, {**bind, "uuid": "other"}],
            [physical, {**bind, "fstype": "xfs"}],
            [physical, {**bind, "maj:min": "111:222"}],
            [physical, {**bind, "fsroot": "/"}],
            [physical, {**bind, "fsroot": "/sibling"}],
            [
                physical,
                bind,
                {
                    **bind,
                    "target": str(self.state / "receipts"),
                    "fsroot": "/state/receipts",
                },
            ],
        ]
        for rows in wrong_rows:
            with (
                self.subTest(rows=rows),
                mock.patch.object(
                    admission.subprocess,
                    "check_output",
                    return_value=json.dumps({"filesystems": rows}),
                ),
                self.assertRaisesRegex(ValueError, "volume identity differs"),
            ):
                admission._check_reserve(self.source, self.state, self.policy)

        nested = self.state / "nested"
        nested.mkdir()
        with mock.patch.object(
            admission.subprocess,
            "check_output",
            return_value=json.dumps({"filesystems": [physical, bind]}),
        ):
            with self.assertRaisesRegex(ValueError, "volume identity differs"):
                admission._check_reserve(
                    self.source, nested, {**self.policy, "state": str(nested)}
                )

    def test_changed_helper_hash_is_never_executed(self):
        with mock.patch.object(
            admission, "_root_file", return_value=b"raise AssertionError()"
        ):
            with self.assertRaisesRegex(ValueError, "helper changed"):
                admission._helper(self.policy)

    def test_bounded_scratch_requires_verified_backing_and_the_parent_reserve(self):
        physical, bind = self.mount_rows()
        scratch = self.base.parent / "private-scratch"
        spec = {"mount": str(scratch)}
        fs = types.SimpleNamespace(f_frsize=4096, f_bavail=self.policy["reserve_bytes"] // 4096 + 8)
        with (
            mock.patch.object(admission.subprocess, "check_output", return_value=json.dumps({"filesystems": [physical, bind]})),
            mock.patch.object(admission.os, "statvfs", return_value=fs),
            mock.patch.object(admission, "_compressed_scratch", return_value=scratch) as verified,
        ):
            policy = {**self.policy, "scratch": spec}
            self.assertEqual(admission._check_reserve(self.source, self.state, policy), scratch)
            verified.assert_called_once_with(spec, self.base, self.base.stat().st_dev)
            fs.f_bavail -= 1
            with self.assertRaisesRegex(OSError, "insufficient space"):
                admission._check_reserve(self.source, self.state, policy)

    def test_enrollment_schema_cannot_accidentally_select_or_omit_scratch(self):
        for schema, extra in (("v1", {"scratch": {}}), ("v2", {})):
            with self.subTest(schema=schema):
                policy = {**self.policy, **extra, "schema": "financial-evidence.native-storage-admission." + schema}
                with mock.patch.object(admission, "_root_file", return_value=json.dumps(policy).encode()):
                    with self.assertRaisesRegex(ValueError, "invalid native storage admission policy"):
                        with admission.storage_admission(self.source, self.state, self.base / "policy"):
                            self.fail("admitted a mixed enrollment")
