"""Opt-in application identities and bounded, server-observed usage.

A credential identifies one installation, never an independent organization.
No IP address, user agent, referrer, contact information or plaintext key is stored.
"""

import argparse
from contextlib import contextmanager
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
import uuid

from .reliability import now, timestamp

CLASSES = ("unverified", "internal", "synthetic", "external_verified")
TOKEN = re.compile(r"fe_[A-Za-z0-9_-]{43}")


def day():
    return timestamp(now()).date()


@contextmanager
def connect(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / "applications.sqlite"
    if path.is_symlink():
        raise ValueError("invalid application storage")
    db = sqlite3.connect(path, timeout=5)
    path.chmod(0o600)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript(
            """
        CREATE TABLE IF NOT EXISTS applications (
          id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
          created_day TEXT NOT NULL, last_seen_day TEXT NOT NULL,
          traffic_class TEXT NOT NULL, evidence_sha256 TEXT);
        CREATE TABLE IF NOT EXISTS completions (
          application TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
          day TEXT NOT NULL, packet TEXT NOT NULL, traffic_class TEXT NOT NULL,
          PRIMARY KEY(application, day, packet, traffic_class));
        CREATE TABLE IF NOT EXISTS cohorts (
          application TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
          traffic_class TEXT NOT NULL, first_day TEXT NOT NULL,
          PRIMARY KEY(application, traffic_class));
        CREATE TABLE IF NOT EXISTS aggregates (
          day TEXT NOT NULL, traffic_class TEXT NOT NULL, outcome TEXT NOT NULL,
          count INTEGER NOT NULL, PRIMARY KEY(day, traffic_class, outcome));
        CREATE INDEX IF NOT EXISTS completion_day ON completions(day);
        CREATE INDEX IF NOT EXISTS application_created ON applications(created_day);
        CREATE INDEX IF NOT EXISTS application_last_seen ON applications(last_seen_day);
        CREATE TABLE IF NOT EXISTS workflow_completions (
          application TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
          day TEXT NOT NULL, workflow TEXT NOT NULL, packet TEXT NOT NULL,
          traffic_class TEXT NOT NULL,
          PRIMARY KEY(application, day, workflow, packet, traffic_class));
        CREATE INDEX IF NOT EXISTS workflow_completion_day ON workflow_completions(day);
        """
        )
        db.execute(
            "DELETE FROM completions WHERE day < ?",
            ((day() - timedelta(days=89)).isoformat(),),
        )
        db.execute(
            "DELETE FROM aggregates WHERE day < ?",
            ((day() - timedelta(days=89)).isoformat(),),
        )
        db.execute("DELETE FROM workflow_completions WHERE day < ?", ((day() - timedelta(days=89)).isoformat(),))
        db.execute(
            "DELETE FROM applications WHERE last_seen_day < ?",
            ((day() - timedelta(days=179)).isoformat(),),
        )
        db.commit()
        yield db
        db.commit()
    finally:
        db.close()


def excluded(headers):
    return bool(
        headers.get("x-operator-probe")
        or headers.get("x-liquilens-traffic-class", "").lower()
        in {"operator", "internal", "synthetic", "test"}
        or headers.get("x-traffic-class", "").lower()
        in {"operator", "internal", "synthetic", "test"}
    )


def enroll(root, body, headers):
    if (
        not isinstance(body, dict)
        or body != {"measurement_consent": True}
        or body["measurement_consent"] is not True
    ):
        raise ValueError("explicit measurement consent is required")
    token = "fe_" + secrets.token_urlsafe(32)
    identifier = uuid.uuid4().hex
    today = day().isoformat()
    classification = "internal" if excluded(headers) else "unverified"
    with connect(root) as db:
        db.execute("BEGIN IMMEDIATE")
        if (
            db.execute("SELECT count(*) FROM applications").fetchone()[0] >= 10000
            or db.execute(
                "SELECT count(*) FROM applications WHERE created_day=?", (today,)
            ).fetchone()[0]
            >= 100
        ):
            raise OverflowError("application enrollment allowance reached")
        db.execute(
            "INSERT INTO applications VALUES (?, ?, ?, ?, ?, NULL)",
            (
                identifier,
                hashlib.sha256(token.encode()).hexdigest(),
                today,
                today,
                classification,
            ),
        )
    return {
        "application_id": identifier,
        "token": token,
        "token_type": "Bearer",
        "classification": classification,
        "independent_ownership_verified": False,
        "quota": "same_bounded_public_service",
        "completion_retention_days": 90,
        "credential_expiry": "180_days_without_accepted_use",
        "erase": "DELETE /v1/applications/current",
    }


def identify(root, authorization, headers):
    if not authorization:
        return {
            "id": None,
            "traffic_class": "synthetic" if excluded(headers) else "anonymous",
        }
    if not authorization.startswith("Bearer ") or not TOKEN.fullmatch(
        authorization[7:]
    ):
        raise PermissionError("invalid application credential")
    digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
    with connect(root) as db:
        row = db.execute(
            "SELECT id, traffic_class FROM applications WHERE token_hash=?", (digest,)
        ).fetchone()
    if row is None:
        raise PermissionError("invalid or expired application credential")
    return {"id": row[0], "traffic_class": "synthetic" if excluded(headers) else row[1]}


def record(root, identity, packet, *, unchanged=False, workflow=None):
    """Count prepared data responses; deduplicate same app/day/packet across routes."""
    today = day().isoformat()
    if workflow is not None and workflow not in {"funding", "institutions", "exit"}:
        raise ValueError("Invalid research workflow")
    classification = identity["traffic_class"]
    outcome = "not_modified" if unchanged else "data_response"
    with connect(root) as db:
        db.execute(
            "INSERT INTO aggregates VALUES (?, ?, ?, 1) ON CONFLICT(day,traffic_class,outcome) "
            "DO UPDATE SET count=min(count+1,1000000)",
            (today, classification, outcome),
        )
        if identity["id"]:
            db.execute(
                "UPDATE applications SET last_seen_day=? WHERE id=?",
                (today, identity["id"]),
            )
        if unchanged or not identity["id"]:
            return False
        # Bounded storage; saturation is explicit and never represented as full coverage.
        if (
            db.execute(
                "SELECT count(*) FROM completions WHERE day=?", (today,)
            ).fetchone()[0]
            >= 50000
        ):
            return False
        changed = db.execute(
            "INSERT OR IGNORE INTO completions VALUES (?, ?, ?, ?)",
            (identity["id"], today, packet, classification),
        ).rowcount
        db.execute(
            "INSERT OR IGNORE INTO cohorts VALUES (?, ?, ?)",
            (identity["id"], classification, today),
        )
        if workflow and db.execute("SELECT count(*) FROM workflow_completions WHERE day=?", (today,)).fetchone()[0] < 50000:
            db.execute("INSERT OR IGNORE INTO workflow_completions VALUES (?, ?, ?, ?, ?)", (identity["id"], today, workflow, packet, classification))
        return bool(changed)


def erase(root, identity):
    if not identity["id"]:
        raise PermissionError("application credential required")
    with connect(root) as db:
        db.execute("DELETE FROM applications WHERE id=?", (identity["id"],))
    return {
        "deleted": True,
        "credential_revoked": True,
        "anonymous_aggregate_counts_retained": True,
    }


def classify(root, identifier, classification, evidence=None):
    if classification not in (
        "internal",
        "unverified",
        "external_verified",
    ) or not re.fullmatch("[a-f0-9]{32}", identifier):
        raise ValueError("invalid reviewed application classification")
    digest = None
    if classification == "external_verified":
        raw = Path(evidence).read_bytes() if evidence else b""
        if not raw or len(raw) > 16384:
            raise ValueError("bounded independent ownership evidence required")
        value = json.loads(raw)
        if (
            value.get("application_id") != identifier
            or value.get("independent_operator") is not True
            or not value.get("basis")
        ):
            raise ValueError("independent ownership review does not match application")
        digest = hashlib.sha256(raw).hexdigest()
    with connect(root) as db:
        if (
            db.execute(
                "UPDATE applications SET traffic_class=?, evidence_sha256=? WHERE id=?",
                (classification, digest, identifier),
            ).rowcount
            != 1
        ):
            raise ValueError("unknown application")
    return {
        "application_id": identifier,
        "classification": classification,
        "evidence_sha256": digest,
        "past_completions_reclassified": False,
    }


def report(root):
    today = day()
    cutoff = (today - timedelta(days=89)).isoformat()
    with connect(root) as db:
        events = db.execute(
            "SELECT application, day, packet, traffic_class FROM completions"
        ).fetchall()
        cohorts = db.execute(
            "SELECT application, traffic_class, first_day FROM cohorts WHERE first_day>=?",
            (cutoff,),
        ).fetchall()
        aggregates = db.execute(
            "SELECT day, traffic_class, outcome, count FROM aggregates"
        ).fetchall()
    result = {}
    for classification in CLASSES:
        selected = [row for row in events if row[3] == classification]
        retention = {}
        for days in (7, 30):
            eligible = [
                (app, first)
                for app, group, first in cohorts
                if group == classification
                and timestamp(first + "T00:00:00Z").date() + timedelta(days=days)
                < today
            ]
            returns = sum(
                any(
                    row[0] == app
                    and row[1]
                    == (
                        timestamp(first + "T00:00:00Z").date() + timedelta(days=days)
                    ).isoformat()
                    for row in selected
                )
                for app, first in eligible
            )
            retention[str(days)] = {
                "eligible_applications": len(eligible),
                "returned_on_day": returns,
                "rate": returns / len(eligible) if eligible else None,
            }
        result[classification] = {
            "applications_with_data_responses": len({row[0] for row in selected}),
            "deduplicated_data_responses": len(selected),
            "retention": retention,
        }
    return {
        "schema": "financial-evidence.application-usage.v1",
        "evaluated_at": now(),
        "retention_days": 90,
        "classes": result,
        "request_aggregates": [
            dict(zip(("day", "traffic_class", "outcome", "count"), row))
            for row in aggregates
        ],
        "cohort_basis": "first_observed_data_response_in_each_server_assigned_class; completed_UTC_return_day",
        "deduplication": "application_UTC_day_packet_class; HTTP_304_is_not_a_data_completion",
        "coverage": "observed_server_responses_only; outages_and_storage_saturation_are_not_proven_nonuse",
        "independent_organizations": None,
        "downstream_users": None,
        "scope": "server_prepared_responses_not_client_delivery_or_measured_customer_value",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("report", "classify"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--application")
    parser.add_argument(
        "--classification", choices=("unverified", "internal", "external_verified")
    )
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    value = (
        report(args.directory)
        if args.operation == "report"
        else classify(
            args.directory, args.application or "", args.classification, args.evidence
        )
    )
    print(json.dumps(value, indent=2))


if __name__ == "__main__":
    main()
