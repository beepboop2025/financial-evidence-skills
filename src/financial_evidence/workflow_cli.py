"""Main-product commands for repeat reviews and explicitly enabled contributions."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from . import research
from .agent_workflow import AgentWorkflow
from .hosted import PLATFORM_URL
from .learning import contracts as c
from .learning.client import RemoteLearningClient


def add_parser(commands):
    workflow = commands.add_parser("workflow", help="run repeatable research, review history and optional outcome reporting")
    sub = workflow.add_subparsers(dest="workflow_command", required=True)
    run = sub.add_parser("run", help="check source status, fetch evidence and compare the previous review")
    run.add_argument("task", choices=research.DEFAULTS)
    run.add_argument("--selection")
    run.add_argument("--mode", choices=sorted(c.MODES), default="unknown")
    run.add_argument("--share-usage", action="store_true", help="queue bounded usage with a separately enrolled credential")
    run.add_argument("--format", choices=("json", "markdown"), default="markdown")
    feedback = sub.add_parser("feedback", help="explicitly confirm whether a retained review was useful")
    feedback.add_argument("run_id")
    choice = feedback.add_mutually_exclusive_group(required=True)
    choice.add_argument("--useful", action="store_true")
    choice.add_argument("--not-useful", action="store_true")
    feedback.add_argument("--share", action="store_true")
    decision = sub.add_parser("decision", help="bind supplied numeric decision evidence to a retained run")
    decision.add_argument("run_id")
    decision.add_argument("--record", required=True, type=Path)
    decision.add_argument("--share", action="store_true")
    outcome = sub.add_parser("outcome", help="record a supplied outcome for a retained decision")
    outcome.add_argument("--record", required=True, type=Path)
    outcome.add_argument("--share", action="store_true")
    deliver = sub.add_parser("deliver", help="retry queued records; exact receipt matching is required")
    deliver.add_argument("--limit", type=int, default=10)
    report = sub.add_parser("report", help="inspect local workflow history, usefulness and delivery status")
    show = sub.add_parser("show", help="read one retained review without fetching or uploading")
    show.add_argument("run_id")
    history = sub.add_parser("history", help="list retained review IDs and statuses without reading source payloads")
    history.add_argument("--limit", type=int, default=20)
    discard = sub.add_parser("discard-pending", help="erase queued submissions and stop local retries")
    for command in (run, feedback, decision, outcome, deliver, report, show, history, discard):
        command.add_argument("--state", required=True, help="owned private directory for this workflow journal")
        if command in (run, feedback, decision, outcome, deliver):
            command.add_argument("--learning-endpoint", default=PLATFORM_URL + "/learning",
                                 help="explicit enrolled destination; never an automatic fallback")
        command.set_defaults(handler=execute)


def _record(path):
    with path.open("rb") as source:
        raw = source.read(65537)
    if len(raw) > 65536:
        raise ValueError("learning record exceeds 64 KiB")
    return json.loads(raw, object_pairs_hook=research._object)


def execute(args):
    try:
        sharing = getattr(args, "share", False) or getattr(args, "share_usage", False) or args.workflow_command == "deliver"
        client = None
        if sharing:
            credential = os.environ.get("FINANCIAL_LEARNING_CREDENTIAL")
            if not credential:
                raise ValueError("explicit sharing requires FINANCIAL_LEARNING_CREDENTIAL from separate enrollment")
            client = RemoteLearningClient(args.learning_endpoint, credential)
        workflow = AgentWorkflow(args.state, mode=getattr(args, "mode", "unknown"), learning=client,
                                 share_usage=getattr(args, "share_usage", False))
        if args.workflow_command == "run":
            result = workflow.run(args.task, args.selection)
            if args.format == "markdown":
                print("Run:", result["run_id"])
                print("Status:", result["status"])
                context = result.get("context") or {}
                print("Source monitor:", context.get("client_monitor_status", "unavailable"))
                for product in context.get("products", []):
                    if product.get("product") == {"funding": "seiche", "institutions": "liquilens", "exit": "undertow"}[args.task]:
                        print("Source coverage:", product.get("freshness_at_evaluation", "unknown"))
                if result["result"] is not None:
                    print(research.render_review(result["result"], result["comparison"]))
                print("Sharing:", result["measurement"]["sharing"])
                print("Next: repeat this command for a comparison; use workflow feedback to confirm usefulness.")
            else:
                print(json.dumps(result, indent=2, allow_nan=False))
            return 0 if result["status"] == "ready_for_review" else 2
        if args.workflow_command == "feedback":
            result = workflow.feedback(args.run_id, useful=args.useful, share=args.share)
        elif args.workflow_command == "decision":
            result = workflow.record_decision(args.run_id, _record(args.record), share=args.share)
        elif args.workflow_command == "outcome":
            result = workflow.record_outcome(_record(args.record), share=args.share)
        elif args.workflow_command == "deliver":
            result = workflow.deliver(limit=args.limit)
        elif args.workflow_command == "show":
            result = workflow.state.run(args.run_id)
        elif args.workflow_command == "history":
            result = workflow.state.history(limit=args.limit)
        elif args.workflow_command == "discard-pending":
            result = workflow.state.discard_pending()
        else:
            result = workflow.report()
        print(json.dumps(result, indent=2, allow_nan=False))
        if args.workflow_command == "deliver":
            return 2 if any(result["outbox"].get(key, 0) for key in ("pending", "sending", "rejected", "expired")) else 0
        return 0
    except (OSError, ValueError, TypeError, sqlite3.Error):
        # Source records and filesystem paths may be private. Print no raw exception body.
        print(json.dumps({"status": "failed", "reason": "invalid_input_or_local_state",
                          "help": "Check the selected workflow, private state directory, record contract and explicit learning enrollment."}))
        return 1
