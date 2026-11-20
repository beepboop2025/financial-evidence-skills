#!/usr/bin/env python3
"""Build the private generation-aware runtime from the pinned, installed 0.1.7 wheel."""
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

BASE_SHA = "673fb9f20d7c2a21a1dc6f55252410e1e5ecb783b5889db79e305e39e8583e92"
COMPAT_SOURCE = "a15dd1251a5d9cc826f80ae326fc6f6e3c6ba15e"
VERSION = "0.1.7+successor.1"
BASE_INFO = "financial_evidence-0.1.7.dist-info/"
INFO = f"financial_evidence-{VERSION}.dist-info/"
ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(original, output):
    archive = original.read_bytes()
    if sha(archive) != BASE_SHA:
        raise ValueError("runtime baseline wheel differs from verified v0.1.7")
    with zipfile.ZipFile(io.BytesIO(archive)) as reader:
        files = {name.replace(BASE_INFO, INFO, 1): reader.read(name) for name in reader.namelist()}
    for name, expected in {
        "financial_evidence/runtime/history.py": "e7c9dedfaab83fcd3c8ad5f7b4c10f67757bf1ec337f78e3d0ea145207d79644",
        "financial_evidence/runtime/store.py": "97bc499601547ec6825c3fab75c769991c9bf096e77a65b0680fabd306e6b420",
    }.items():
        raw = (ROOT / "src" / name).read_bytes()
        if sha(raw) != expected:
            raise ValueError(f"reviewed successor runtime source changed: {name}")
        files[name] = raw
    for name, before, after in (
        (INFO + "METADATA", b"\nVersion: 0.1.7\n", f"\nVersion: {VERSION}\n".encode()),
        ("financial_evidence/__init__.py", b'__version__ = "0.1.7"', f'__version__ = "{VERSION}"'.encode()),
    ):
        if files[name].count(before) != 1:
            raise ValueError("baseline wheel metadata differs")
        files[name] = files[name].replace(before, after)
    record = INFO + "RECORD"
    del files[record]
    listing = io.StringIO(newline="")
    writer = csv.writer(listing, lineterminator="\n")
    for name, raw in sorted(files.items()):
        content = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip("=")
        writer.writerow([name, "sha256=" + content, len(raw)])
    writer.writerow([record, "", ""])
    files[record] = listing.getvalue().encode()
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_STORED) as writer:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 20, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            writer.writestr(info, raw)
    implementation = {
        name.removeprefix("financial_evidence/"): sha(raw) for name, raw in files.items()
        if name.startswith("financial_evidence/") and name.endswith(".py")
    }
    wheel = output / f"financial_evidence-{VERSION}-py3-none-any.whl"
    contents = payload.getvalue()
    with wheel.open("xb") as stream:
        stream.write(contents)
    return {
        "package_version": VERSION,
        "source_commit": COMPAT_SOURCE,
        "base_wheel_sha256": BASE_SHA,
        "wheel_sha256": sha(contents),
        "implementation_sha256": sha(json.dumps(implementation, sort_keys=True, separators=(",", ":")).encode()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.base_wheel, args.output), indent=2, sort_keys=True))
