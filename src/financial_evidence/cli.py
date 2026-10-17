"""Command-line interface for public financial evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Iterable
from typing import Any

from . import __version__
from .core import ALIASES, ROUTES, build_packet, normalize_topics, route_manifest


# Legacy process codes are intentionally keyed to transport reachability only.
STATUS_EXIT = {"complete": 0, "partial": 1, "unavailable": 2}


def compact_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _topic_values(args: argparse.Namespace, *, default_all: bool = False) -> list[str]:
    values = args.topic or (list(ROUTES) if default_all else [])
    return normalize_topics(values)


def _route_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"topic": topic, **source}
        for topic, sources in manifest["topics"].items()
        for source in sources
    ]


def _source_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    packet_semantics = {
        key: packet[key]
        for key in (
            "status",
            "transport_status",
            "status_semantics",
            "evidence_status",
            "carrier_verification",
        )
    }
    for source in packet["sources"]:
        row = {
            **packet_semantics,
            **{
                key: value
                for key, value in source.items()
                if key not in {"document", "source_reported"}
            },
        }
        for key in ("source_reported", "document"):
            if key in source:
                row[key] = compact_json(source[key])
        rows.append(row)
    return rows


def emit_rows(rows: list[dict[str, Any]], output_format: str) -> None:
    if output_format == "ndjson":
        for row in rows:
            print(compact_json(row))
        return
    if output_format == "csv":
        fields: list[str] = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return
    raise ValueError(f"unsupported row format {output_format!r}")


def emit_table(rows: list[dict[str, Any]], fields: Iterable[str]) -> None:
    selected = list(fields)
    widths = {
        field: max(
            len(field),
            *(len(str(row.get(field, ""))) for row in rows),
        )
        for field in selected
    }
    print("  ".join(field.ljust(widths[field]) for field in selected))
    print("  ".join("-" * widths[field] for field in selected))
    for row in rows:
        print(
            "  ".join(
                str(row.get(field, "")).ljust(widths[field]) for field in selected
            )
        )


def command_topics(args: argparse.Namespace) -> int:
    rows = [
        {
            "topic": topic,
            "products": ",".join(source.product for source in sources),
            "aliases": ",".join(
                alias for alias, canonical in ALIASES.items() if canonical == topic
            ),
        }
        for topic, sources in ROUTES.items()
    ]
    if args.format == "json":
        print(compact_json({"topics": rows}))
    else:
        emit_table(rows, ("topic", "products", "aliases"))
    return 0


def command_route(args: argparse.Namespace) -> int:
    topics = _topic_values(args, default_all=True)
    manifest = route_manifest(topics)
    if args.format == "json":
        print(compact_json(manifest))
    elif args.format == "table":
        emit_table(
            _route_rows(manifest),
            (
                "topic",
                "product",
                "evidence_class",
                "url",
                "human_scope_url",
                "financial_authority",
                "carrier_state",
            ),
        )
    else:
        emit_rows(_route_rows(manifest), args.format)
    return 0


def command_fetch(args: argparse.Namespace) -> int:
    topics = _topic_values(args)
    packet = build_packet(
        topics,
        max_bytes=args.max_bytes,
        timeout=args.timeout,
    )
    if args.format == "json":
        print(compact_json(packet))
    else:
        emit_rows(_source_rows(packet), args.format)
    return STATUS_EXIT[packet["transport_status"]]


def command_doctor(args: argparse.Namespace) -> int:
    args.topic = list(ROUTES)
    return command_fetch(args)


def command_start(args: argparse.Namespace) -> int:
    """Choose a useful task before installing clients or fetching data."""
    from .onboarding import starter_catalog

    catalog = starter_catalog()
    if args.task:
        catalog["tasks"] = [task for task in catalog["tasks"] if task["id"] == args.task]
    for task in catalog["tasks"]:
        task["review_command"] = (
            f"financial-evidence review {task['id']} --selection {task['selection']} --output reviews"
        )
    if args.format == "json":
        print(compact_json(catalog))
        return 0
    print("Choose one research task. No network request has been made.\n")
    for task in catalog["tasks"]:
        print(f"{task['title']} ({task['product']})")
        print(task["question"])
        print("  Run:", task["review_command"])
        print("  Browser:", task["browser_url"])
        print("  API:", task["api_url"])
        print("  MCP:", task["tool"], compact_json(task["arguments"]))
        print("  Scope:", task["scope"], "\n")
    print("MCP connection:", catalog["mcp_url"])
    print("A saved review includes result.json, brief.md and a receipt. At your next review,")
    print("repeat the same command with --previous PATH/TO/result.json to compare evidence.")
    print("Use --verification for operator tests. Requests are not proof of adoption.")
    return 0


def command_review(args: argparse.Namespace) -> int:
    from .onboarding import TASKS
    from .research import main as review_main

    task = next(task for task in TASKS if task["id"] == args.workflow)
    argv = ["--workflow", args.workflow, "--selection",
            args.selection if args.selection is not None else task["selection"],
            "--format", args.format]
    for option in ("output", "previous"):
        if getattr(args, option) is not None:
            argv.extend(["--" + option, getattr(args, option)])
    if args.verification:
        argv.append("--verification")
    return review_main(argv)


COMPLETIONS = {
    "bash": """_financial_evidence() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  COMPREPLY=( $(compgen -W "start review mcp topics route fetch doctor completion --help --version" -- "$cur") )
}
complete -F _financial_evidence financial-evidence
""",
    "zsh": """#compdef financial-evidence
_arguments '1:command:(start review mcp topics route fetch doctor completion)' '*::arg:->args'
""",
    "fish": """complete -c financial-evidence -f -a 'start review mcp topics route fetch doctor completion'
complete -c financial-evidence -l version -d 'Show version'
""",
}


def command_completion(args: argparse.Namespace) -> int:
    print(COMPLETIONS[args.shell], end="")
    return 0


def _add_topic_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--topic",
        action="append",
        default=[],
        help="repeat or comma-separate topic aliases",
    )


def _add_fetch_limits(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-bytes", type=int, default=4_194_304)
    parser.add_argument("--timeout", type=float, default=10.0)


def command_mcp(args: argparse.Namespace) -> int:
    """Expose stdio under the package-name executable used by registries."""
    from .mcp import main as mcp_main

    return mcp_main()


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="financial-evidence",
        description="Route and fetch bounded public financial evidence.",
    )
    root.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = root.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="choose a research task; show CLI, API and MCP setup offline")
    start.add_argument("task", nargs="?", choices=("funding", "institutions", "exit"))
    start.add_argument("--format", choices=("text", "json"), default="text")
    start.set_defaults(handler=command_start)

    review = commands.add_parser("review", help="read one workflow, save a brief and compare a previous review")
    review.add_argument("workflow", choices=("funding", "institutions", "exit"))
    review.add_argument("--selection", help="currency, covered institution slugs or BTC USD sizes")
    review.add_argument("--output", help="directory for new captures; existing reviews are preserved")
    review.add_argument("--previous", help="previous result.json for the same workflow and selection")
    review.add_argument("--format", choices=("markdown", "json"), default="markdown")
    review.add_argument("--verification", action="store_true", help="label operator or CI tests as synthetic")
    review.set_defaults(handler=command_review)

    mcp = commands.add_parser("mcp", help="serve the read-only MCP router on stdio")
    mcp.set_defaults(handler=command_mcp)

    topics = commands.add_parser("topics", help="list canonical topics and aliases")
    topics.add_argument("--format", choices=("json", "table"), default="table")
    topics.set_defaults(handler=command_topics)

    route = commands.add_parser("route", help="print fixed routes without fetching")
    _add_topic_argument(route)
    route.add_argument(
        "--format", choices=("json", "ndjson", "csv", "table"), default="json"
    )
    route.set_defaults(handler=command_route)

    fetch = commands.add_parser("fetch", help="fetch a bounded evidence packet")
    _add_topic_argument(fetch)
    _add_fetch_limits(fetch)
    fetch.add_argument("--format", choices=("json", "ndjson", "csv"), default="json")
    fetch.set_defaults(handler=command_fetch)

    doctor = commands.add_parser("doctor", help="check every fixed public route")
    _add_fetch_limits(doctor)
    doctor.add_argument("--format", choices=("json", "ndjson", "csv"), default="json")
    doctor.set_defaults(handler=command_doctor)

    completion = commands.add_parser("completion", help="emit shell completion")
    completion.add_argument("shell", choices=tuple(COMPLETIONS))
    completion.set_defaults(handler=command_completion)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if hasattr(args, "max_bytes") and not 1 <= args.max_bytes <= 4_194_304:
        parser().error("--max-bytes must be between 1 and 4194304")
    if hasattr(args, "timeout") and not 0 < args.timeout <= 30:
        parser().error("--timeout must be greater than 0 and at most 30 seconds")
    try:
        return int(args.handler(args))
    except ValueError as exc:
        parser().error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
