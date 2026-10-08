"""Self-service research runtime, with explicit local storage and no hidden daemon."""

import argparse
import os
from pathlib import Path
import sys
import time

from .catalog import manifest
from .contracts import Workflow, decode, encode, presets
from .engine import Runtime, verify_bundle
from .store import Store


def read(path, limit=2_097_152):
    with Path(path).open("rb") as stream:
        return decode(stream.read(limit + 1), limit=limit)


def write_new(path, value):
    raw = encode(value) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local durable financial research workflows; no order execution.")
    parser.add_argument("--root", help="Private per-installation state directory; required for stateful commands")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    p = sub.add_parser("presets")
    p.add_argument("--id", choices=[row["id"] for row in presets()])
    p = sub.add_parser("verify")
    p.add_argument("file")
    p = sub.add_parser("init")
    p.add_argument("--traffic-class", choices=["unverified", "internal", "synthetic"], default="unverified")
    p = sub.add_parser("register")
    p.add_argument("file")
    sub.add_parser("jobs")
    p = sub.add_parser("run")
    p.add_argument("job")
    p.add_argument("--key", required=True)
    p = sub.add_parser("tick")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("replay")
    p.add_argument("run_id")
    p = sub.add_parser("export")
    p.add_argument("run_id")
    p.add_argument("--output", required=True)
    p = sub.add_parser("events")
    p.add_argument("--after", type=int, default=0)
    p.add_argument("--limit", type=int, default=100)
    sub.add_parser("metrics")
    sub.add_parser("stop")
    sub.add_parser("resume")
    for action in ("pause", "enable"):
        p = sub.add_parser(action)
        p.add_argument("job")
    p = sub.add_parser("acknowledge")
    p.add_argument("run_id")
    p.add_argument("--outcome", required=True, choices=["useful", "not_useful"])
    p.add_argument("--confirm-local-report", action="store_true", required=True)
    p = sub.add_parser("backup")
    p.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = manifest()
        elif args.command == "presets":
            result = next(row for row in presets() if row["id"] == args.id) if args.id else presets()
        elif args.command == "verify":
            result = verify_bundle(read(args.file))
        else:
            if not args.root:
                raise ValueError("--root is required; state is never stored implicitly")
            store = Store(args.root, traffic_class=args.traffic_class if args.command == "init" else None)
            runtime = Runtime(store)
            if args.command in ("init", "metrics"):
                result = store.report()
            elif args.command == "register":
                result = store.register(Workflow.parse(read(args.file, 8192)), time.time())
            elif args.command == "jobs":
                result = {"jobs": store.jobs()}
            elif args.command == "run":
                result = runtime.run(args.job, "manual:" + args.key)
            elif args.command == "tick":
                result = runtime.tick(args.limit)
            elif args.command == "replay":
                result = runtime.replay(args.run_id)
            elif args.command == "export":
                bundle = runtime.bundle(args.run_id)
                write_new(args.output, bundle)
                result = {"path": args.output, **verify_bundle(bundle)}
            elif args.command == "events":
                result = store.events(args.after, args.limit)
            elif args.command in ("stop", "resume"):
                result = store.control(time.time(), stopped=args.command == "stop")
            elif args.command in ("pause", "enable"):
                result = store.control(time.time(), job=args.job, enabled=args.command == "enable")
            elif args.command == "acknowledge":
                result = store.acknowledge(args.run_id, args.outcome, time.time())
            elif args.command == "backup":
                result = store.backup(args.output)
        print(encode(result).decode())
        return 0
    except (ValueError, OSError, OverflowError) as exc:
        print(encode({"error": type(exc).__name__, "message": str(exc)}).decode(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
