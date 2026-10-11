"""Local administration and explicitly hosted optional ingestion."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .contracts import digest, encode
from .evaluation import evaluate
from .store import LearningStore


def read_json(path):
    source = Path(path)
    if source.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("input file exceeds 16 MiB")
    return json.loads(source.read_text())


def private_write(path, value):
    """New files only, 0600, no accidental replacement of reviewed exports."""
    target = Path(path)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(encode(value) + b"\n")
        output.flush()
        os.fsync(output.fileno())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Explicit financial-agent learning enrollment, review and evaluation")
    parser.add_argument("--store", required=True, help="owned private directory for the separate learning database")
    commands = parser.add_subparsers(dest="command", required=True)
    enroll = commands.add_parser("enroll")
    enroll.add_argument("--purpose", action="append", required=True)
    enroll.add_argument("--policy-version", required=True)
    enroll.add_argument("--expires-at", type=float, required=True, help="UTC Unix seconds")
    enroll.add_argument("--retention-days", type=int, default=90)
    enroll.add_argument("--output", required=True, help="new 0600 file containing the enrollment credential")
    for name in ("event", "decision", "outcome"):
        command = commands.add_parser(name)
        command.add_argument("--credential-file", required=True)
        command.add_argument("--input", required=True)
    for name in ("me", "report", "withdraw", "delete"):
        command = commands.add_parser(name)
        command.add_argument("--credential-file", required=name != "report")
        if name == "withdraw":
            command.add_argument("--purpose", action="append")
            command.add_argument("--delete-records", action="store_true")
    review = commands.add_parser("review-outcome")
    review.add_argument("--tenant", required=True)
    review.add_argument("--outcome", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--verification-reference", required=True)
    admission = commands.add_parser("admit")
    admission.add_argument("--tenant", required=True)
    admission.add_argument("--decision", required=True)
    admission.add_argument("--purpose", required=True)
    admission.add_argument("--reviewer", required=True)
    admission.add_argument("--rights-reference", required=True)
    admission.add_argument("--source-scopes", required=True, help="JSON file mapping each source identifier to the admitted purpose")
    admission.add_argument("--expires-at", type=float, required=True)
    target = commands.add_parser("register-target")
    target.add_argument("--id", required=True)
    target.add_argument("--unit", required=True)
    target.add_argument("--description", required=True)
    verify = commands.add_parser("verify-organisation")
    verify.add_argument("--tenant", required=True)
    verify.add_argument("--verification-reference", required=True)
    export = commands.add_parser("export")
    export.add_argument("--purpose", required=True)
    export.add_argument("--target", default="funding_next_release_change")
    export.add_argument("--as-of", type=float)
    export.add_argument("--output", required=True)
    experiment = commands.add_parser("evaluate")
    experiment.add_argument("--input", required=True)
    experiment.add_argument("--entity")
    experiment.add_argument("--output", required=True)
    experiment.add_argument("--model-id", help="record evaluation artifact and source snapshot lineage")
    commands.add_parser("expire")
    commands.add_parser("lineage")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8091)
    args = parser.parse_args(argv)
    try:
        store = LearningStore(args.store)
        token = None
        credential_file = getattr(args, "credential_file", None)
        if credential_file:
            path = Path(credential_file)
            if path.is_symlink() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
                raise ValueError("credential file must be private, owned and not a symlink")
            token = read_json(path)["credential"]
        if args.command == "enroll":
            result = store.enroll(purposes=args.purpose, policy_version=args.policy_version, expires_at=args.expires_at, retention_days=args.retention_days)
            private_write(args.output, result)
            result = {"tenant_id": result["tenant_id"], "credential_written": True, "organisation_verified": False}
        elif args.command in {"event", "decision", "outcome"}:
            method = {"event": store.record_tool, "decision": store.record_decision, "outcome": store.record_outcome}[args.command]
            result = method(token, read_json(args.input))
        elif args.command == "me":
            result = store.describe(token)
        elif args.command == "report":
            result = store.report(token)
        elif args.command == "withdraw":
            result = store.withdraw(token, purposes=args.purpose, delete=args.delete_records)
        elif args.command == "delete":
            result = store.delete_tenant(token)
        elif args.command == "review-outcome":
            result = store.review_outcome(args.tenant, args.outcome, reviewer=args.reviewer, verification_reference=args.verification_reference)
        elif args.command == "admit":
            result = store.review_contribution(args.tenant, args.decision, purpose=args.purpose, reviewer=args.reviewer,
                                               rights_reference=args.rights_reference, source_scopes=read_json(args.source_scopes), expires_at=args.expires_at)
        elif args.command == "register-target":
            result = store.register_target(identifier=args.id, unit=args.unit, description=args.description)
        elif args.command == "verify-organisation":
            store.review_organisation(args.tenant, verification_reference=args.verification_reference)
            result = {"organisation_verified": True}
        elif args.command == "export":
            result = store.export_dataset(purpose=args.purpose, target=args.target, as_of=args.as_of)
            private_write(args.output, result)
            result = {"snapshot_id": result["manifest"]["id"], "rows": len(result["rows"]), "status": result["status"]}
        elif args.command == "evaluate":
            dataset = read_json(args.input)
            store.validate_snapshot(dataset)
            result = evaluate(dataset, entity=args.entity)
            private_write(args.output, result)
            if args.model_id:
                if result["status"] not in {"evaluated", "evaluated_baseline_only"}:
                    raise ValueError("insufficient data: no trained model can be registered")
                store.record_model(model_id=args.model_id, snapshot_id=result["snapshot_id"], artifact_sha256=digest(result))
            result = {key: value for key, value in result.items() if key not in {"models", "test_predictions"}}
        elif args.command == "expire":
            result = store.expire()
        elif args.command == "lineage":
            result = store.model_lineage()
        else:
            import uvicorn
            from .api import create_app
            uvicorn.run(create_app(store), host=args.host, port=args.port, access_log=False, proxy_headers=False)
            return 0
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, KeyError, OSError, OverflowError) as exc:
        # Validation messages never include ingested bodies or credential values.
        print("learning command failed: " + str(exc), file=sys.stderr)
        return 2
