#!/usr/bin/env python3
"""Validate the description users will see in a built Python wheel on PyPI."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def _name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _description(value: str) -> str:
    # Wheel metadata serialization may change line endings or the final newline.
    return value.replace("\r\n", "\n").rstrip("\n")


def verify(wheel: Path, *, pyproject: Path = ROOT / "pyproject.toml") -> dict:
    # The release build uses Python 3.13. Keep the reusable wheel checks below
    # importable by the package's Python 3.10 test matrix without a TOML extra.
    try:
        import tomllib
    except ModuleNotFoundError as exc:
        raise ValueError("the release CLI requires Python 3.11+ to read pyproject.toml") from exc
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    readme = project["readme"]
    if isinstance(readme, str):
        readme_path = pyproject.parent / readme
        content_type = "text/markdown" if readme_path.suffix == ".md" else "text/x-rst"
    else:
        readme_path = pyproject.parent / readme["file"]
        content_type = readme["content-type"]
    return verify_metadata(wheel, project=project, readme_path=readme_path, content_type=content_type)


def verify_metadata(wheel: Path, *, project: dict, readme_path: Path,
                    content_type: str = "text/markdown") -> dict:
    expected_description = readme_path.read_text(encoding="utf-8")
    with ZipFile(wheel) as archive:
        entries = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(entries) != 1:
            raise ValueError("wheel must contain exactly one dist-info/METADATA")
        metadata = BytesParser(policy=policy.default).parsebytes(archive.read(entries[0]))
    name, version = metadata.get("Name"), metadata.get("Version")
    if not name or _name(name) != _name(project["name"]):
        raise ValueError("wheel Name differs from pyproject.toml")
    if version != project["version"]:
        raise ValueError("wheel Version differs from pyproject.toml")
    if metadata.get("Summary") != project["description"]:
        raise ValueError("wheel Summary differs from pyproject.toml")
    if metadata.get("Description-Content-Type", "").split(";", 1)[0] != content_type:
        raise ValueError("wheel Description-Content-Type differs from configured README")
    description = metadata.get_payload(decode=True).decode("utf-8")
    if _description(description) != _description(expected_description):
        raise ValueError("wheel description differs from configured README")

    # Check explicit self-install requirements, including extras and normalized
    # distribution spellings, without policing unrelated prose or dependencies.
    package_pattern = r"[-_.]+".join(re.escape(part) for part in _name(name).split("-"))
    pins = re.finditer(
        rf"(?<![\w.-]){package_pattern}(?:\[[A-Za-z0-9_., -]+\])?\s*==\s*"
        r"(?P<version>[A-Za-z0-9](?:[A-Za-z0-9.!+_-]*[A-Za-z0-9])?)",
        description,
        re.IGNORECASE,
    )
    for pin in pins:
        if pin["version"] != version:
            raise ValueError(f"README installation pin {pin['version']} differs from wheel Version {version}")

    # A current package guide must not silently send readers to older tagged
    # instructions. Historical release notes and other repositories are distinct.
    source = project.get("urls", {}).get("Source", "").removesuffix("/").removesuffix(".git")
    parsed_source = urlparse(source)
    if parsed_source.netloc == "github.com":
        repository = parsed_source.path.strip("/")
        guide_pattern = (
            rf"https://(?:github\.com/{re.escape(repository)}/(?:blob|tree)/"
            rf"|raw\.githubusercontent\.com/{re.escape(repository)}/)"
            r"v(?P<version>[^/\s]+)/docs/"
        )
        for guide in re.finditer(guide_pattern, description):
            if guide["version"] != version:
                raise ValueError(f"README guide version {guide['version']} differs from wheel Version {version}")

    return {
        "schema": "financial-evidence.pypi-metadata-check.v1",
        "status": "PASS",
        "wheel": str(wheel),
        "name": name,
        "version": version,
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "readme": str(readme_path),
        "description_sha256": hashlib.sha256(_description(description).encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", type=Path, nargs="+")
    parser.add_argument("--pyproject", type=Path, default=ROOT / "pyproject.toml")
    args = parser.parse_args()
    try:
        results = [verify(wheel, pyproject=args.pyproject) for wheel in args.wheels]
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"PyPI metadata verification failed: {exc}\n")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
