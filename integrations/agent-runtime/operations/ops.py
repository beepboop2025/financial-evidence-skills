#!/usr/bin/env python3
"""Private operations for an explicitly configured Financial Evidence runtime."""

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import sys
import time

from ops_backup import backup, recover
from ops_common import OPS_VERSION, config, decode, encode, private, regular
from ops_monitor import dashboard, monitor
from ops_recovery import candidates, recover_snapshot
from ops_diagnostics import diagnose


def handler(cfg):
    class Handler(BaseHTTPRequestHandler):
        server_version = "FinancialEvidenceOperations/" + OPS_VERSION

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_):
            pass  # Do not retain access URLs or invent application/user telemetry.

        def do_GET(self):
            port = self.server.server_address[1]
            if self.headers.get("Host") not in {"127.0.0.1:" + str(port), "localhost:" + str(port)}:
                self.send_error(421)
                return
            status = 200
            if self.path == "/":
                body, content_type = dashboard(), "text/html; charset=utf-8"
            elif self.path == "/diagnostics.json":
                try:
                    value = decode(regular(Path(cfg["state"]) / "diagnostics.json", 1_048_576), limit=1_048_576)
                    if datetime.fromisoformat(value["valid_until"]).timestamp() < time.time():
                        value = {**value, "status": "stale"}
                    status = 200 if value.get("status") == "observed" else 503
                    body, content_type = encode(value), "application/json"
                except (OSError, ValueError, KeyError, TypeError):
                    status = 503
                    body, content_type = b'{"status":"unavailable"}', "application/json"
            elif self.path in {"/status.json", "/metrics"}:
                try:
                    value = decode(regular(Path(cfg["state"]) / "health.json", 262144), limit=262144)
                    expires = datetime.fromisoformat(value["valid_until"]).timestamp()
                    if expires < time.time():
                        value = {**value, "operations_status": "stale", "monitor_stale": True}
                        status = 503
                    elif value["operations_status"] == "critical":
                        status = 503
                    if self.path == "/status.json":
                        body, content_type = encode(value), "application/json"
                    else:
                        from ops_monitor import metrics
                        body, content_type = metrics(value), "text/plain; version=0.0.4"
                except (OSError, ValueError, KeyError, TypeError):
                    status = 503
                    body, content_type = b'{"operations_status":"unavailable","source_status":"unknown"}', "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.send_error(405)

    return Handler


def serve(cfg, port):
    if not 1024 <= port <= 65535:
        raise ValueError("unprivileged local port required")
    private(cfg["state"])
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(cfg))
    server.daemon_threads = True
    server.serve_forever()


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("monitor")
    sub.add_parser("backup")
    sub.add_parser("status")
    sub.add_parser("recovery-candidates")
    command = sub.add_parser("diagnose")
    command.add_argument("--job")
    command = sub.add_parser("serve")
    command.add_argument("--port", type=int, default=8768)
    command = sub.add_parser("restore")
    command.add_argument("--receipt", required=True)
    command.add_argument("--target", required=True)
    command = sub.add_parser("restore-snapshot")
    command.add_argument("--snapshot", required=True)
    command.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    try:
        cfg = config(args.config)
        if args.command == "monitor":
            result = monitor(cfg)
            print(encode(result).decode())
            return 2 if result["operations_status"] == "critical" else 0
        if args.command == "backup":
            result = backup(cfg)
        elif args.command == "restore":
            result = recover(cfg, args.receipt, args.target)
        elif args.command == "recovery-candidates":
            result = candidates(cfg)
        elif args.command == "restore-snapshot":
            result = recover_snapshot(cfg, args.snapshot, args.target)
        elif args.command == "diagnose":
            result = diagnose(cfg, job=args.job)
        elif args.command == "serve":
            serve(cfg, args.port)
            return 0
        else:
            result = decode(regular(Path(cfg["state"]) / "health.json", 262144), limit=262144)
            if datetime.fromisoformat(result["valid_until"]).timestamp() < time.time():
                result = {**result, "operations_status": "stale", "monitor_stale": True}
        print(encode(result).decode())
        return 0 if result.get("operations_status") not in {"critical", "stale"} else 2
    except Exception as error:
        # Provider errors can contain credentials. Local detailed state remains
        # available without reflecting arbitrary exception text into logs.
        print(encode({"status": "failed", "error_type": type(error).__name__}).decode(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
