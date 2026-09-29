"""Forward-only public evidence packets and private, consented usage counters."""

import argparse
import fcntl
import hashlib
import hmac
import json
import os
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from . import funding_archive
from .original_publishers import build as build_original_review
from .reliability import (
    RELEASE,
    SOURCE,
    encoded,
    fetch,
    now,
    sample,
    strict_json,
    summarize,
    timestamp,
)

CAPTURE = re.compile(r"\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{32}")
TOKEN = re.compile(r"[0-9a-f]{32}")
SITE = "https://beepboop2025.github.io"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    if path.is_symlink() or path.stat().st_size > 262144:
        raise ValueError("invalid stored artifact")
    return strict_json(path.read_bytes())


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())


def replace(path, value):
    temporary = path.with_name("." + path.name + "-" + uuid.uuid4().hex)
    write_new(temporary, value)
    os.replace(temporary, path)


def verify_pair(review, csv_raw):
    """A CSV from a different capture must never be attached to this review."""
    capture_id = review.get("capture_id", "")
    if not CAPTURE.fullmatch(capture_id) or review.get("schema") not in (
        "liquidity-lab.funding-review.v1",
        "financial-evidence.original-publisher-review.v1",
    ):
        raise ValueError("unsupported review")
    if (
        review.get("observed_release", {}).get("source_commit") != SOURCE
        or review.get("runtime_release", {}).get("source_commit") != SOURCE
    ):
        raise ValueError("review release mismatch")
    if (
        review.get("release_identity") != "matched"
        or review.get("runtime_release_identity") != "matched"
    ):
        raise ValueError("unverified release")
    if review.get("available") is not True or review.get("stale") is not False:
        raise ValueError("review unavailable or stale")
    scope = funding_archive._scope(review)
    report = dict(
        review, status=review["data_readiness"], evaluated_at=review["captured_at"]
    )
    rows = funding_archive._rows(csv_raw, review["captured_at"], report, scope)
    for row in rows:
        expected_unit = "%" if row["metric_id"] in funding_archive.METRICS[:4] else "$B"
        if row["unit"] != expected_unit:
            raise ValueError("unexpected metric unit")
    public = review.get("results")
    if not isinstance(public, list) or len(public) != len(rows):
        raise ValueError("review row count mismatch")
    for expected, actual in zip(rows, public):
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError("CSV and review disagree")
    return rows


def archive_once(
    root,
    *,
    trigger="schedule",
    fetcher=fetch,
    builder=build_original_review,
    perspective="hetzner_same_host",
):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for child in ("packets", "attempts", "publisher-blobs"):
        (root / child).mkdir(exist_ok=True)
    with (root / ".archive.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identifier = uuid.uuid4().hex
        probe, docs = sample(
            perspective=perspective,
            trigger=trigger,
            run_id=identifier,
            fetcher=fetcher,
        )
        attempt = {
            "schema": "financial-evidence.packet-attempt.v1",
            "attempt_id": identifier,
            "probe": probe,
            "packet_id": None,
            "error": None,
        }
        try:
            if not probe["available"] or not probe["release_matches"]:
                raise ValueError("service_or_release_unavailable")
            receipt, csv_raw = fetcher("/api/v1/funding-review.csv")
            attempt["csv_request"] = receipt
            if receipt["http_status"] != 200 or receipt["error"]:
                raise ValueError("CSV unavailable")
            review = docs["review"]
            verify_pair(review, csv_raw)
            review, csv_raw, publisher_sources = builder(review)
            verify_pair(review, csv_raw)
            for _, raw, receipt in publisher_sources:
                blob = root / "publisher-blobs" / receipt["sha256"]
                if blob.exists():
                    if (
                        blob.is_symlink()
                        or digest(blob.read_bytes()) != receipt["sha256"]
                    ):
                        raise ValueError("publisher blob changed")
                else:
                    with blob.open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
            capture_id = review["capture_id"]
            folder = root / "packets" / capture_id
            if folder.exists():
                old, prior_raw, _ = packet(root, capture_id)
                if old["source_manifest_sha256"] != review["manifest_sha256"]:
                    raise ValueError("capture identity changed")
                if strict_json(prior_raw)["results"] != review["results"]:
                    raise ValueError(
                        "publisher observation changed within reference capture"
                    )
            else:
                staging = root / "packets" / (".staging-" + identifier)
                staging.mkdir()
                review_raw = encoded(review)
                for name, raw in (
                    ("review.json", review_raw),
                    ("observations.csv", csv_raw),
                ):
                    with (staging / name).open("xb") as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                manifest = {
                    "schema": "financial-evidence.public-packet.v1",
                    "packet_id": capture_id,
                    "archived_at": now(),
                    "source_captured_at": review["captured_at"],
                    "source_manifest_sha256": review["manifest_sha256"],
                    "source_response_sha256": probe["requests"]["review"][
                        "body_sha256"
                    ],
                    "knowledge_time_basis": "first_verified_in_this_forward_archive",
                    "source_release": RELEASE,
                    "source_commit": SOURCE,
                    "producer_source_commit": os.environ.get(
                        "FINANCIAL_EVIDENCE_SOURCE_COMMIT", "unknown"
                    ),
                    "producer_modules_sha256": {
                        name: digest(Path(__file__).with_name(name).read_bytes())
                        for name in (
                            "institutional.py",
                            "original_publishers.py",
                            "reliability.py",
                            "funding_archive.py",
                        )
                    },
                    "method_version": review.get(
                        "method_version", "synthetic_test_fixture"
                    ),
                    "review_asof": review.get("review_asof"),
                    "review_scope": review.get("review_scope"),
                    "latest_per_instrument": False,
                    "ready_at_capture": review["ready"],
                    "artifacts": {
                        "review.json": digest(review_raw),
                        "observations.csv": digest(csv_raw),
                    },
                    "publisher_receipts": {
                        name: receipt for name, _, receipt in publisher_sources
                    },
                    "value_basis": review.get("value_basis", "synthetic_test_fixture"),
                }
                write_new(staging / "manifest.json", manifest)
                os.rename(staging, folder)
            attempt["packet_id"] = capture_id
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            ParseError,
            BadZipFile,
        ) as error:
            attempt["error"] = type(error).__name__ + ": " + str(error)[:140]
        attempt["recorded_at"] = now()
        probe["workspace_ready"] = probe["ready"]
        probe["ready"] = bool(
            probe["ready"]
            and attempt["error"] is None
            and attempt["packet_id"] is not None
        )
        probe["includes_original_publisher_checks"] = True
        write_new(root / "attempts" / (identifier + ".json"), attempt)
        replace(
            root / "latest.json",
            {"attempt_id": identifier, "sha256": digest(encoded(attempt))},
        )
        observations = [
            read_json(p)["probe"] for p in (root / "attempts").glob("*.json")
        ]
        replace(root / "reliability.json", summarize(observations))
        replace(root / "coverage.json", history(root))
        return attempt


def packet(root, identifier):
    if not CAPTURE.fullmatch(identifier):
        raise ValueError("invalid packet id")
    folder = Path(root) / "packets" / identifier
    if folder.is_symlink():
        raise ValueError("invalid packet folder")
    manifest = read_json(folder / "manifest.json")
    if (
        manifest.get("schema") != "financial-evidence.public-packet.v1"
        or manifest.get("packet_id") != identifier
    ):
        raise ValueError("invalid packet manifest")
    values = []
    for name in ("review.json", "observations.csv"):
        path = folder / name
        if path.is_symlink() or path.stat().st_size > 131072:
            raise ValueError("invalid packet artifact")
        raw = path.read_bytes()
        if digest(raw) != manifest["artifacts"][name]:
            raise ValueError("packet hash mismatch")
        values.append(raw)
    verify_pair(strict_json(values[0]), values[1])
    return manifest, *values


def history(root, *, as_of=None, limit=96):
    cutoff = timestamp(as_of or now())
    if cutoff > timestamp(now()):
        raise ValueError("future as-of is unsupported")
    rows = []
    for folder in (Path(root) / "packets").iterdir():
        if CAPTURE.fullmatch(folder.name):
            manifest = read_json(folder / "manifest.json")
            if timestamp(manifest["archived_at"]) <= cutoff:
                rows.append(
                    {
                        key: manifest[key]
                        for key in (
                            "packet_id",
                            "archived_at",
                            "source_captured_at",
                            "review_asof",
                            "ready_at_capture",
                            "source_manifest_sha256",
                        )
                    }
                )
    rows.sort(key=lambda x: (timestamp(x["archived_at"]), x["packet_id"]))
    attempts = [read_json(p) for p in (Path(root) / "attempts").glob("*.json")]
    known = [a for a in attempts if timestamp(a["recorded_at"]) <= cutoff]
    last = max(known, key=lambda a: timestamp(a["recorded_at"]), default=None)
    return {
        "schema": "financial-evidence.forward-coverage.v1",
        "as_of": cutoff.isoformat(),
        "knowledge_time_basis": "first_verified_in_this_forward_archive",
        "scope": "observed_packets_only_not_complete_publisher_vintages",
        "first_archived_at": rows[0]["archived_at"] if rows else None,
        "last_archived_at": rows[-1]["archived_at"] if rows else None,
        "packet_count": len(rows),
        "packets": rows[-limit:],
        "truncated": len(rows) > limit,
        "latest_attempt": {k: last[k] for k in ("recorded_at", "packet_id", "error")}
        if last
        else None,
    }


def latest(root):
    reference = read_json(Path(root) / "latest.json")
    if not TOKEN.fullmatch(reference["attempt_id"]):
        raise ValueError("invalid attempt id")
    attempt = read_json(Path(root) / "attempts" / (reference["attempt_id"] + ".json"))
    if digest(encoded(attempt)) != reference["sha256"]:
        raise ValueError("attempt integrity mismatch")
    age = (
        timestamp(now()) - timestamp(attempt["probe"]["observed_at"])
    ).total_seconds()
    source_age = attempt["probe"].get("capture_age_seconds")
    source_current = (
        isinstance(source_age, (int, float))
        and not isinstance(source_age, bool)
        and 0 <= source_age + age <= 1200
    )
    usable = (
        attempt["packet_id"] is not None
        and attempt["error"] is None
        and 0 <= age <= 1200
        and source_current
    )
    return {
        "available": usable,
        "ready": usable and attempt["probe"]["ready"],
        "age_seconds": age,
        "attempt": attempt,
        "packet": packet(root, attempt["packet_id"])[0] if usable else None,
    }


def compare(root, left, right):
    a, ar, _ = packet(root, left)
    b, br, _ = packet(root, right)
    if timestamp(a["archived_at"]) > timestamp(b["archived_at"]):
        raise ValueError("comparison must run forward")
    before, after = strict_json(ar)["results"], strict_json(br)["results"]
    changes = []
    keys = ("value", "unit", "observation_date", "value_state", "source")
    for old, new in zip(before, after):
        if old["metric_id"] != new["metric_id"]:
            raise ValueError("different metric sets")
        if any(old[k] != new[k] for k in keys):
            changes.append(
                {
                    "metric_id": old["metric_id"],
                    "kind": "new_observation_date"
                    if old["observation_date"] != new["observation_date"]
                    else "same_date_observation_changed",
                    "before": {k: old[k] for k in keys},
                    "after": {k: new[k] for k in keys},
                }
            )
    return {
        "before": left,
        "after": right,
        "changes": changes,
        "scope": "captured_differences_not_confirmed_publisher_revision_events",
    }


def connect_events(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = root / "visitor.key"
    if not key.exists():
        temporary = root / (".key-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as stream:
                stream.write(os.urandom(32))
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            os.link(temporary, key)
        except FileExistsError:
            pass
        finally:
            temporary.unlink(missing_ok=True)
    if key.is_symlink() or key.stat().st_size != 32:
        raise ValueError("invalid private usage key")
    db = sqlite3.connect(root / "usage.sqlite", timeout=5)
    db.execute(
        "CREATE TABLE IF NOT EXISTS events (visitor TEXT NOT NULL, day TEXT NOT NULL, packet TEXT NOT NULL, kind TEXT NOT NULL, PRIMARY KEY(visitor, day, packet, kind))"
    )
    cutoff = (timestamp(now()) - timedelta(days=29)).date().isoformat()
    db.execute("DELETE FROM events WHERE day < ?", (cutoff,))
    db.commit()
    return db, key.read_bytes()


def usage_event(root, archive, body, *, forget=False):
    expected = (
        {"visitor", "consent"}
        if forget
        else {"visitor", "consent", "packet_id", "kind", "traffic_class"}
    )
    if (
        not isinstance(body, dict)
        or set(body) != expected
        or body.get("consent") is not True
        or not TOKEN.fullmatch(str(body.get("visitor", "")))
    ):
        raise ValueError("explicit consent and a random visitor id are required")
    if not forget and body["traffic_class"] == "operator":
        return {"recorded": False, "reason": "operator_excluded"}
    if not forget:
        if body["kind"] != "packet_download" or body["traffic_class"] != "browser":
            raise ValueError("unsupported event")
        packet(archive, body["packet_id"])
    db, key = connect_events(root)
    with closing(db), db:
        visitor = hmac.new(key, body["visitor"].encode(), hashlib.sha256).hexdigest()
        if forget:
            db.execute("DELETE FROM events WHERE visitor = ?", (visitor,))
            result = {"deleted": True}
        else:
            day = timestamp(now()).date().isoformat()
            if (
                db.execute(
                    "SELECT count(*) FROM events WHERE day = ?", (day,)
                ).fetchone()[0]
                >= 5000
                or db.execute(
                    "SELECT count(*) FROM events WHERE day = ? AND visitor = ?",
                    (day, visitor),
                ).fetchone()[0]
                >= 50
            ):
                raise ValueError("daily event allowance reached")
            cursor = db.execute(
                "INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?)",
                (visitor, day, body["packet_id"], body["kind"]),
            )
            result = {
                "recorded": bool(cursor.rowcount),
                "scope": "unverified_consented_browser_event",
            }
    return result


def usage_report(root):
    db, _ = connect_events(root)
    cutoff = (timestamp(now()) - timedelta(days=13)).date().isoformat()
    rows = db.execute(
        "SELECT visitor, count(DISTINCT day) FROM events WHERE day >= ? GROUP BY visitor",
        (cutoff,),
    ).fetchall()
    total = db.execute("SELECT count(*) FROM events").fetchone()[0]
    db.close()
    return {
        "evaluated_at": now(),
        "retention_days": 30,
        "consented_download_events": total,
        "anonymous_visitors_14d": len(rows),
        "visitors_on_3_days_in_14d": sum(days >= 3 for _, days in rows),
        "verified_fund_organizations": None,
        "verified_fund_basis": "organization_verification_is_not_inferred_from_anonymous_events",
        "scope": "client_reported_usage_not_fund_adoption_or_analyst_time_saved",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("archive", "history", "usage"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--trigger", choices=("manual", "schedule"), default="schedule")
    args = parser.parse_args()
    if args.command == "archive":
        value = archive_once(args.directory, trigger=args.trigger)
    elif args.command == "history":
        value = history(args.directory, as_of=args.as_of)
    else:
        value = usage_report(args.directory)
    print(json.dumps(value, indent=2))
    return 1 if args.command == "archive" and value["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
