#!/usr/bin/env python3
"""Keep the package-free research download identical to the packaged client."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = (ROOT / "src/financial_evidence/research.py").read_bytes()
    target = ROOT / "docs/start/research_watch.py"
    if args.check:
        if target.read_bytes() != source:
            parser.error("Run python3 scripts/build_research_watch.py to synchronize the download")
    else:
        target.write_bytes(source)


if __name__ == "__main__":
    main()
