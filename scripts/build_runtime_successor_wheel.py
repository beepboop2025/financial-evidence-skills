#!/usr/bin/env python3
"""Build the private generation-aware runtime from the pinned, installed 0.1.7 wheel."""
import argparse
import base64
import csv
import hashlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
import zipfile

BASE_SHA = "673fb9f20d7c2a21a1dc6f55252410e1e5ecb783b5889db79e305e39e8583e92"
COMPAT_SOURCE = "a15dd1251a5d9cc826f80ae326fc6f6e3c6ba15e"
TRANSPORT_SOURCE = "b8ab5c3339183338159d9292c2c9cf818390b417"
BASE_SERVICE_SHA = "89c1d7a7d614a1fa36ad9f8a3e5cdb158bad158077002f3f6d0a9df10dfbc548"
SERVICE_SHA = "bd309386a61720aa43306675317a8e301d8f73a3c52e736033abca4948e14528"
PATCH_SHA = "0bf8fc5a8828bdf1cffc42d0437a6da5e1c4655c6b853bdd4beb3e89d988c0c6"
BASE_INFO = "financial_evidence-0.1.7.dist-info/"
ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def patch_atlas_budget(service, output):
    """Apply the reviewed public transport delta to pristine 0.1.7 bytes."""
    patch = ROOT / "integrations/agent-runtime/successor-runtime/atlas-read-budget.patch"
    if sha(service) != BASE_SERVICE_SHA or sha(patch.read_bytes()) != PATCH_SHA:
        raise ValueError("baseline service or reviewed transport patch differs")
    with tempfile.TemporaryDirectory(dir=output) as temp:
        path = Path(temp) / "src/financial_evidence/service.py"
        path.parent.mkdir(parents=True)
        path.write_bytes(service)
        subprocess.run(["git", "init", "--quiet", temp], check=True)
        subprocess.run(["git", "apply", "--whitespace=error", str(patch)], cwd=temp, check=True)
        updated = path.read_bytes()
    if sha(updated) != SERVICE_SHA:
        raise ValueError("patched baseline service differs from the qualified transport module")
    return updated


def build(original, output, profile="1"):
    if profile not in {"1", "2"}:
        raise ValueError("unknown private runtime profile")
    version = "0.1.7+successor." + profile
    info_dir = f"financial_evidence-{version}.dist-info/"
    archive = original.read_bytes()
    if sha(archive) != BASE_SHA:
        raise ValueError("runtime baseline wheel differs from verified v0.1.7")
    with zipfile.ZipFile(io.BytesIO(archive)) as reader:
        files = {name.replace(BASE_INFO, info_dir, 1): reader.read(name) for name in reader.namelist()}
    for name, expected in {
        "financial_evidence/runtime/history.py": "e7c9dedfaab83fcd3c8ad5f7b4c10f67757bf1ec337f78e3d0ea145207d79644",
        "financial_evidence/runtime/store.py": "97bc499601547ec6825c3fab75c769991c9bf096e77a65b0680fabd306e6b420",
    }.items():
        raw = (ROOT / "integrations/agent-runtime/successor-runtime" / Path(name).name).read_bytes()
        if sha(raw) != expected:
            raise ValueError(f"reviewed successor runtime source changed: {name}")
        files[name] = raw
    transport = {}
    if profile == "2":
        path = "financial_evidence/service.py"
        files[path] = patch_atlas_budget(files[path], output)
        transport = {"transport_source_commit": TRANSPORT_SOURCE,
                     "base_service_sha256": BASE_SERVICE_SHA, "service_sha256": SERVICE_SHA}
    for name, before, after in (
        (info_dir + "METADATA", b"\nVersion: 0.1.7\n", f"\nVersion: {version}\n".encode()),
        ("financial_evidence/__init__.py", b'__version__ = "0.1.7"', f'__version__ = "{version}"'.encode()),
    ):
        if files[name].count(before) != 1:
            raise ValueError("baseline wheel metadata differs")
        files[name] = files[name].replace(before, after)
    record = info_dir + "RECORD"
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
    wheel = output / f"financial_evidence-{version}-py3-none-any.whl"
    contents = payload.getvalue()
    with wheel.open("xb") as stream:
        stream.write(contents)
    return {
        "package_version": version,
        **transport,
        "source_commit": COMPAT_SOURCE,
        "base_wheel_sha256": BASE_SHA,
        "wheel_sha256": sha(contents),
        "implementation_sha256": sha(json.dumps(implementation, sort_keys=True, separators=(",", ":")).encode()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("1", "2"), default="1")
    args = parser.parse_args()
    print(json.dumps(build(args.base_wheel, args.output, args.profile), indent=2, sort_keys=True))
