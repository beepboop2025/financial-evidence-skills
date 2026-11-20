"""Coordinate full funding backup restores with an enrolled native storage owner."""

from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import types


class StorageBusy(Exception):
    """The existing storage owner is active and no backup work has started."""


def _root_file(path, maximum):
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("storage policy path is not a direct absolute path")
    for parent in path.parents:
        info = parent.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("storage policy directory is not root-controlled")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(fd)
        if (
            info.st_uid != 0
            or not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_mode & 0o022
            or info.st_size > maximum
        ):
            raise ValueError("storage policy file custody differs")
        data = stream.read(maximum + 1)
        if len(data) > maximum:
            raise ValueError("storage policy file exceeds its size bound")
        return data


def _helper(policy):
    path = Path(policy["helper"])
    source = _root_file(path, 64 * 1024)
    if hashlib.sha256(source).hexdigest() != policy["helper_sha256"]:
        raise ValueError("enrolled storage admission helper changed")
    module = types.ModuleType("funding_enrolled_storage")
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _stage_bytes(source, block_size):
    # Include directories, filesystem block rounding, and one metadata block per
    # member. The original archive verifier still admits and hashes each file.
    def allocated(path):
        size = path.stat(follow_symlinks=False).st_size
        return (1 + (size + block_size - 1) // block_size) * block_size

    total = allocated(source / "current.json")

    for folder in (source / "captures").iterdir():
        if folder.is_symlink() or not (folder / "manifest.json").is_file():
            continue
        total += allocated(folder)
        total += sum(allocated(member) for member in folder.iterdir())
    return total


def _check_reserve(source, state, policy):
    mount = Path(policy["mount"])
    if (
        state != Path(policy["state"])
        or state.resolve(strict=True) != state
        or state == mount
        or not state.is_relative_to(mount)
        or mount.resolve(strict=True) != mount
    ):
        raise ValueError("backup scratch differs from the enrolled volume")
    device = mount.stat().st_dev
    physical = {
        "uuid": policy["uuid"],
        "fstype": policy["filesystem"],
        "target": str(mount),
        "fsroot": "/",
        "maj:min": f"{os.major(device)}:{os.minor(device)}",
    }
    # ProtectSystem=strict may expose the original ReadWritePaths directory as
    # a separate mount of precisely that same subdirectory of the filesystem.
    self_bind = {
        **physical,
        "target": str(state),
        "fsroot": "/" + str(state.relative_to(mount)),
    }
    output = subprocess.check_output(
        [
            "/usr/bin/findmnt",
            "--json",
            "--list",
            "--submounts",
            "--target",
            str(mount),
            "--output",
            "UUID,FSTYPE,TARGET,FSROOT,MAJ:MIN",
        ],
        text=True,
        timeout=10,
    )
    relevant = []
    for row in json.loads(output)["filesystems"]:
        target = Path(row["target"])
        if state.is_relative_to(target) or target.is_relative_to(state):
            relevant.append(row)
    relevant.sort(key=lambda row: row["target"])
    if state.stat().st_dev != device or relevant not in (
        [physical],
        [physical, self_bind],
    ):
        raise ValueError("backup volume identity differs")
    required = policy["reserve_bytes"] + _stage_bytes(
        source, os.statvfs(state).f_frsize
    )
    usage = os.statvfs(state)
    if usage.f_bavail * usage.f_frsize < required:
        raise OSError(
            "insufficient space for a full restore above the enrolled reserve"
        )


@contextmanager
def storage_admission(source, state, policy_path):
    policy = json.loads(_root_file(policy_path, 16 * 1024))
    if (
        policy.get("schema") != "financial-evidence.native-storage-admission.v1"
        or set(policy)
        != {
            "schema",
            "helper",
            "helper_sha256",
            "state",
            "mount",
            "uuid",
            "filesystem",
            "reserve_bytes",
        }
        or not re.fullmatch(r"[0-9a-f]{64}", policy["helper_sha256"])
        or type(policy["reserve_bytes"]) is not int
        or policy["reserve_bytes"] <= 0
    ):
        raise ValueError("invalid native storage admission policy")
    guard = _helper(policy)
    with ExitStack() as entered:
        try:
            entered.enter_context(
                guard.admission(include_existing_ci=True, wait_seconds=60)
            )
        except ValueError as error:
            if str(error) != "Storage admission is held by another job":
                raise
            raise StorageBusy from error
        _check_reserve(source, state, policy)
        yield
