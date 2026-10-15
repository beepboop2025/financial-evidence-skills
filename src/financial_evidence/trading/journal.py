"""Immutable local captures; no upload or rights expansion implied by a receipt."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def save_receipt(directory, receipt):
    """Create a content-addressed 0600 capture under an owner-only directory.

    Preserve permitted product outputs locally; the caller controls capture rights.
    A digest proves unchanged local bytes, not source truth or a trusted timestamp.
    """
    root = Path(directory).absolute()
    if root.is_symlink():
        raise ValueError("receipt directory itself must not be a symlink")
    # The managed SSD workspace and macOS /var are legitimate parent aliases.
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = root.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("receipt directory must be owned by the current user with mode 0700")
    raw = _encode(receipt)
    if len(raw) > 4_194_304:
        raise ValueError("receipt too large")
    sha = hashlib.sha256(raw).hexdigest()
    path = root / f"{sha}.json"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        existing = os.lstat(path)
        if not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid() or stat.S_IMODE(existing.st_mode) & 0o077:
            raise ValueError("unsafe existing receipt")
        if path.read_bytes() != raw:
            raise ValueError("immutable receipt mismatch")
    else:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return {"kind": "product", "product": receipt["product"], "receipt_id": sha,
            "sha256": sha, "path": str(path), "verification": "local_content_hash_only"}


def read_receipt(path):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 4_194_304:
        raise ValueError("unsafe receipt")
    raw = path.read_bytes()
    if path.stem != hashlib.sha256(raw).hexdigest():
        raise ValueError("receipt digest mismatch")
    return json.loads(raw)
