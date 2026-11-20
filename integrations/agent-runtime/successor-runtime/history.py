"""Read sealed predecessor receipts while preserving their original canonical bytes."""

import hashlib
import zlib

from .contracts import MAX_BUNDLE_BYTES


def receipt_bytes(db, row):
    """Return the canonical payload and its predecessor identity, if archived."""
    raw = row["bundle"]
    origin = None
    if raw is None and row["sha256"] is not None:
        if db.execute("PRAGMA user_version").fetchone()[0] != 2:
            raise ValueError("missing receipt")
        archived = db.execute(
            "SELECT payload,raw_size FROM predecessor_runs WHERE run_id=?", (row["id"],)
        ).fetchone()
        if (
            archived is None
            or not isinstance(archived[0], bytes)
            or type(archived[1]) is not int
            or not 0 < archived[1] <= MAX_BUNDLE_BYTES
            or len(archived[0]) > MAX_BUNDLE_BYTES + 1024
        ):
            raise ValueError("invalid predecessor receipt")
        decoder = zlib.decompressobj()
        try:
            raw = decoder.decompress(archived[0], archived[1] + 1)
        except zlib.error as error:
            raise ValueError("invalid compressed predecessor receipt") from error
        if len(raw) != archived[1] or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("invalid predecessor receipt length")
        origin = db.execute("SELECT installation_id FROM predecessor").fetchone()[0]
    if raw is not None and hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("receipt integrity mismatch")
    return raw, origin
