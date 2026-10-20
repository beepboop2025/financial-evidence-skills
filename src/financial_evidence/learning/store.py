"""Opt-in local ledger. No runtime hooks, implicit enrollment or remote sending.

Local administrator methods (enroll, review, export, lineage) are intentionally
absent from the HTTP API. A holder of an ingestion credential cannot admit its
own data for shared training or certify itself as an institution.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid

from . import contracts as c

DAY = 86400


class PermissionDenied(ValueError):
    """Missing, expired or withdrawn purpose permission."""


class LearningStore:
    def __init__(self, path, clock=time.time):
        self.root = Path(path).expanduser().absolute()
        self.clock = clock
        if self.root.is_symlink():
            raise ValueError("learning root cannot be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.root.is_dir() or self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise ValueError("learning root must be owned and private (0700)")
        self.path = self.root / "learning.sqlite"
        self._check_paths()
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(descriptor)
        with self.connection() as db:
            if db.execute("PRAGMA user_version").fetchone()[0] not in (0, 1):
                raise ValueError("unsupported learning database version")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY, credential_hash TEXT NOT NULL UNIQUE,
                    enrolled REAL NOT NULL, retention_days INTEGER NOT NULL,
                    organisation_verified INTEGER NOT NULL DEFAULT 0, verification_reference TEXT);
                CREATE TABLE IF NOT EXISTS permissions (
                    id TEXT PRIMARY KEY, tenant TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    purpose TEXT NOT NULL, policy_version TEXT NOT NULL, granted REAL NOT NULL,
                    expires REAL NOT NULL, status TEXT NOT NULL DEFAULT 'active',
                    UNIQUE(tenant,purpose));
                CREATE TABLE IF NOT EXISTS records (
                    tenant TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, sha256 TEXT NOT NULL,
                    received REAL NOT NULL, expires REAL NOT NULL,
                    PRIMARY KEY(tenant,kind,id));
                CREATE INDEX IF NOT EXISTS records_expiry ON records(expires);
                CREATE TABLE IF NOT EXISTS outcome_reviews (
                    tenant TEXT NOT NULL, outcome_id TEXT NOT NULL, reviewer TEXT NOT NULL,
                    reference TEXT NOT NULL, reviewed REAL NOT NULL, PRIMARY KEY(tenant,outcome_id));
                CREATE TABLE IF NOT EXISTS admissions (
                    id TEXT PRIMARY KEY, tenant TEXT NOT NULL, decision_id TEXT NOT NULL,
                    outcome_id TEXT NOT NULL, purpose TEXT NOT NULL, rights_reference TEXT NOT NULL,
                    reviewer TEXT NOT NULL, reviewed REAL NOT NULL, expires REAL NOT NULL,
                    sha256 TEXT NOT NULL, source_scopes TEXT NOT NULL,
                    UNIQUE(tenant,decision_id,purpose));
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, manifest TEXT NOT NULL, sha256 TEXT NOT NULL,
                    created REAL NOT NULL, invalidated INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    artifact_sha256 TEXT NOT NULL, created REAL NOT NULL, needs_review INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS targets (id TEXT PRIMARY KEY, spec TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at REAL NOT NULL,
                    action TEXT NOT NULL, reference TEXT NOT NULL);
                PRAGMA user_version=1;
            """)
            db.execute("INSERT OR IGNORE INTO targets VALUES (?,?)", (c.DEFAULT_TARGET["id"], c.encode(c.DEFAULT_TARGET).decode()))

    def _check_paths(self):
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = self.path.with_name(self.path.name + suffix)
            if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1
                    or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077)):
                raise ValueError("learning database files must be owned, private, and not linked")

    @contextmanager
    def connection(self):
        self._check_paths()
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA secure_delete=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _now(self):
        return c.moment(self.clock())

    @staticmethod
    def _hash(credential):
        if not isinstance(credential, str) or not 32 <= len(credential) <= 128:
            raise PermissionDenied("invalid credential")
        return hashlib.sha256(credential.encode()).hexdigest()

    def _tenant(self, db, credential):
        hashed = self._hash(credential)
        row = db.execute("SELECT * FROM tenants WHERE credential_hash=?", (hashed,)).fetchone()
        if row is None or not hmac.compare_digest(row["credential_hash"], hashed):
            raise PermissionDenied("invalid credential")
        return row

    @staticmethod
    def _permission(db, tenant, purpose, now):
        permission = db.execute("SELECT * FROM permissions WHERE tenant=? AND purpose=?", (tenant, purpose)).fetchone()
        if permission is None or permission["status"] != "active" or permission["expires"] <= now:
            raise PermissionDenied(f"active {purpose} permission required")
        return permission

    @staticmethod
    def _audit(db, at, action, reference):
        db.execute("INSERT INTO audit(at,action,reference) VALUES (?,?,?)", (at, action, reference))

    def enroll(self, *, purposes, policy_version, expires_at, retention_days=90):
        """Local owner enrollment; returns the only plaintext copy of its credential."""
        now = self._now()
        c.label(policy_version, "policy_version")
        if not isinstance(purposes, (list, tuple)) or not purposes or len(set(purposes)) != len(purposes) or set(purposes) - c.PURPOSES:
            raise ValueError("invalid purpose selection")
        if set(purposes) & c.TRAINING and "private_evidence" not in purposes:
            raise ValueError("training permission requires private_evidence permission")
        if isinstance(retention_days, bool) or not isinstance(retention_days, int) or not 1 <= retention_days <= 365:
            raise ValueError("retention_days must be 1..365")
        if not now < c.moment(expires_at) <= now + 366 * DAY:
            raise ValueError("permission expiry must be within one year")
        identifier, credential = uuid.uuid4().hex, secrets.token_urlsafe(32)
        with self.connection() as db:
            db.execute("INSERT INTO tenants(id,credential_hash,enrolled,retention_days) VALUES (?,?,?,?)",
                       (identifier, self._hash(credential), now, retention_days))
            for purpose in purposes:
                db.execute("INSERT INTO permissions VALUES (?,?,?,?,?,?,'active')",
                           (uuid.uuid4().hex, identifier, purpose, policy_version, now, expires_at))
            self._audit(db, now, "enrolled", identifier)
        return {"tenant_id": identifier, "credential": credential, "purposes": list(purposes),
                "policy_version": policy_version, "expires_at": expires_at, "organisation_verified": False,
                "retention_days": retention_days, "remote_telemetry_enabled": False}

    def _insert(self, db, tenant, kind, value, now, purpose):
        permission = self._permission(db, tenant["id"], purpose, now)
        raw, sha = c.encode(value).decode(), c.digest(value)
        existing = db.execute("SELECT sha256,received FROM records WHERE tenant=? AND kind=? AND id=?",
                              (tenant["id"], kind, value["id"])).fetchone()
        if existing:
            if existing["sha256"] != sha:
                raise ValueError("idempotency conflict: record id already has different content")
            return {"id": value["id"], "sha256": sha, "created": False, "received_at": existing["received"]}
        if db.execute("SELECT count(*) FROM records WHERE tenant=?", (tenant["id"],)).fetchone()[0] >= 100000:
            raise OverflowError("tenant record allowance reached")
        expires = min(permission["expires"], now + tenant["retention_days"] * DAY)
        db.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?)", (tenant["id"], kind, value["id"], raw, sha, now, expires))
        return {"id": value["id"], "sha256": sha, "created": True, "received_at": now}

    def record_tool(self, credential, event):
        now = self._now()
        event = c.tool_event(event, now)
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential)
            permission = self._permission(db, tenant["id"], "measurement", now)
            if event["occurred_at"] < permission["granted"]:
                raise ValueError("measurement cannot backfill activity predating permission")
            return self._insert(db, tenant, "tool", event, now, "measurement")

    def record_decision(self, credential, decision):
        now = self._now()
        decision = c.decision(decision, now)
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential)
            if not db.execute("SELECT 1 FROM targets WHERE id=?", (decision["target"],)).fetchone():
                raise ValueError("target must be registered by the local operator")
            return self._insert(db, tenant, "decision", decision, now, "private_evidence")

    @staticmethod
    def _record(db, tenant, kind, identifier, now):
        row = db.execute("SELECT * FROM records WHERE tenant=? AND kind=? AND id=? AND expires>?",
                         (tenant, kind, identifier, now)).fetchone()
        if row is None:
            raise ValueError("record not found")
        if c.digest(json.loads(row["body"])) != row["sha256"]:
            raise ValueError("record integrity mismatch")
        return row, json.loads(row["body"])

    def record_outcome(self, credential, outcome):
        now = self._now()
        outcome = c.outcome(outcome, now)
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential)
            _, decision = self._record(db, tenant["id"], "decision", outcome["decision_id"], now)
            spec = json.loads(db.execute("SELECT spec FROM targets WHERE id=?", (decision["target"],)).fetchone()[0])
            if outcome["unit"] != spec["unit"]:
                raise ValueError("outcome unit does not match target")
            if outcome["observed_at"] < decision["decided_at"] + decision["horizon_seconds"]:
                raise ValueError("outcome precedes target horizon")
            for row in db.execute("SELECT id,body FROM records WHERE tenant=? AND kind='outcome'", (tenant["id"],)):
                if row["id"] != outcome["id"] and json.loads(row["body"])["decision_id"] == outcome["decision_id"]:
                    raise ValueError("one immutable outcome per decision; use a new decision for another revision")
            result = self._insert(db, tenant, "outcome", outcome, now, "private_evidence")
            return {**result, "verification": "operator_reported"}

    def get_record(self, credential, kind, identifier):
        c.choice(kind, {"tool", "decision", "outcome"}, "record kind")
        now = self._now()
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential)
            row, body = self._record(db, tenant["id"], kind, identifier, now)
            review = db.execute("SELECT 1 FROM outcome_reviews WHERE tenant=? AND outcome_id=?", (tenant["id"], identifier)).fetchone() if kind == "outcome" else None
            return {"record": body, "sha256": row["sha256"], "received_at": row["received"],
                    "verification": "reviewer_verified" if review else "operator_reported",
                    "reference_integrity_is_not_source_verification": True}

    def describe(self, credential):
        now = self._now()
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential)
            permissions = [dict(row) for row in db.execute("SELECT id,purpose,policy_version,granted,expires,status FROM permissions WHERE tenant=? ORDER BY purpose", (tenant["id"],))]
            return {"tenant_id": tenant["id"], "permissions": permissions, "retention_days": tenant["retention_days"],
                    "organisation_verified": bool(tenant["organisation_verified"]), "remote_telemetry_enabled": False}

    def review_organisation(self, tenant_id, *, verification_reference):
        """Local administrator records independent onboarding evidence, never IP inference."""
        c.label(verification_reference)
        with self.connection() as db:
            result = db.execute("UPDATE tenants SET organisation_verified=1,verification_reference=? WHERE id=?", (verification_reference, tenant_id))
            if not result.rowcount:
                raise ValueError("tenant not found")
            self._audit(db, self._now(), "organisation_reviewed", tenant_id)

    def register_target(self, *, identifier, unit, description):
        c.label(identifier)
        c.label(unit)
        if not isinstance(description, str) or not 1 <= len(description) <= 512:
            raise ValueError("target description must contain 1..512 characters")
        spec = {"id": identifier, "unit": unit, "description": description}
        with self.connection() as db:
            existing = db.execute("SELECT spec FROM targets WHERE id=?", (identifier,)).fetchone()
            if existing and json.loads(existing[0]) != spec:
                raise ValueError("target definitions are immutable; create a versioned id")
            db.execute("INSERT OR IGNORE INTO targets VALUES (?,?)", (identifier, c.encode(spec).decode()))
        return spec

    def review_outcome(self, tenant_id, outcome_id, *, reviewer, verification_reference):
        now = self._now()
        c.label(reviewer)
        c.label(verification_reference)
        with self.connection() as db:
            self._expire(db, now)
            self._record(db, tenant_id, "outcome", outcome_id, now)
            db.execute("INSERT INTO outcome_reviews VALUES (?,?,?,?,?) ON CONFLICT(tenant,outcome_id) DO UPDATE SET reviewer=excluded.reviewer,reference=excluded.reference,reviewed=excluded.reviewed",
                       (tenant_id, outcome_id, reviewer, verification_reference, now))
            self._audit(db, now, "outcome_reviewed", outcome_id)
        return {"outcome_id": outcome_id, "verification": "reviewer_verified", "verified_at": now}

    def review_contribution(self, tenant_id, decision_id, *, purpose, reviewer, rights_reference, source_scopes, expires_at):
        """Admit a frozen pair after independent outcome and per-source rights review.

        source_scopes maps every feature/outcome source to its exact admitted use
        (research_training or commercial_training). Unknown/denied/context-only
        sources are rejected, including China series without the required rights.
        The local reviewer is accountable for the supporting rights record.
        """
        now = self._now()
        c.choice(purpose, c.TRAINING, "training purpose")
        for value in (reviewer, rights_reference):
            c.label(value)
        if not now < c.moment(expires_at) <= now + 366 * DAY:
            raise ValueError("admission expiry must be within one year")
        with self.connection() as db:
            self._expire(db, now)
            permission = self._permission(db, tenant_id, purpose, now)
            private = self._permission(db, tenant_id, "private_evidence", now)
            drow, decision = self._record(db, tenant_id, "decision", decision_id, now)
            pairs = [(row, json.loads(row["body"])) for row in db.execute("SELECT * FROM records WHERE tenant=? AND kind='outcome' AND expires>?", (tenant_id, now))]
            pairs = [(row, value) for row, value in pairs if value["decision_id"] == decision_id]
            if len(pairs) != 1:
                raise ValueError("one linked outcome required")
            orow, outcome = pairs[0]
            if not db.execute("SELECT 1 FROM outcome_reviews WHERE tenant=? AND outcome_id=?", (tenant_id, outcome["id"])).fetchone():
                raise ValueError("independent outcome review required before training admission")
            sources = {feature["source"] for kind in ("data_features", "usage_features") for feature in decision[kind].values()} | {outcome["source"]}
            if not isinstance(source_scopes, dict) or set(source_scopes) != sources or any(scope != purpose for scope in source_scopes.values()):
                raise ValueError("every exact source must be admitted for this purpose; unknown/denied/context_only cannot train")
            identifier = uuid.uuid4().hex
            expires = min(expires_at, permission["expires"], private["expires"], drow["expires"], orow["expires"])
            sha = c.digest({"decision": decision, "outcome": outcome})
            db.execute("INSERT INTO admissions VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(tenant,decision_id,purpose) DO UPDATE SET id=excluded.id,outcome_id=excluded.outcome_id,rights_reference=excluded.rights_reference,reviewer=excluded.reviewer,reviewed=excluded.reviewed,expires=excluded.expires,sha256=excluded.sha256,source_scopes=excluded.source_scopes",
                       (identifier, tenant_id, decision_id, outcome["id"], purpose, rights_reference, reviewer, now, expires, sha, c.encode(source_scopes).decode()))
            self._audit(db, now, "contribution_admitted", identifier)
            return {"admission_id": identifier, "purpose": purpose, "expires_at": expires, "sha256": sha}

    def export_dataset(self, *, purpose, target, as_of=None):
        """Local admin snapshot: only live permissions, reviewed sources and labels.

        Exports are explicit, with internal lineage stored separately. No API
        endpoint exposes cross-tenant data, admissions or training exports.
        """
        now = self._now()
        c.choice(purpose, c.TRAINING, "training purpose")
        c.label(target)
        cutoff = now if as_of is None else c.moment(as_of)
        if cutoff > now:
            raise ValueError("snapshot cutoff cannot be in the future")
        rows, lineage = [], []
        with self.connection() as db:
            self._expire(db, now)
            for adm in db.execute("SELECT * FROM admissions WHERE purpose=? AND expires>? AND reviewed<=? ORDER BY decision_id,tenant", (purpose, now, cutoff)).fetchall():
                try:
                    permission = self._permission(db, adm["tenant"], purpose, now)
                    private = self._permission(db, adm["tenant"], "private_evidence", now)
                    drow, decision = self._record(db, adm["tenant"], "decision", adm["decision_id"], now)
                    orow, outcome = self._record(db, adm["tenant"], "outcome", adm["outcome_id"], now)
                except (PermissionDenied, ValueError):
                    continue
                if permission["granted"] > cutoff or private["granted"] > cutoff or drow["received"] > cutoff or orow["received"] > cutoff:
                    continue
                if decision["target"] != target or outcome["available_at"] > cutoff:
                    continue
                if decision["mode"] not in {"shadow", "paper", "operator_reported_production"}:
                    continue
                if adm["sha256"] != c.digest({"decision": decision, "outcome": outcome}):
                    raise ValueError("admitted pair integrity mismatch")
                row_id = c.digest({"tenant": adm["tenant"], "decision": decision["id"]})
                exported_outcome = {key: value for key, value in outcome.items() if key not in {"id", "decision_id"}}
                rows.append({"id": row_id, "entity": decision["entity"], "target": target,
                             "decided_at": decision["decided_at"], "horizon_end": decision["decided_at"] + decision["horizon_seconds"],
                             "decision_received_at": drow["received"], "data_features": decision["data_features"], "usage_features": decision["usage_features"],
                             "outcome": {**exported_outcome, "received_at": orow["received"], "verification": "reviewer_verified"},
                             "mode": decision["mode"]})
                lineage.append({"row_id": row_id, "tenant": adm["tenant"], "decision_id": decision["id"],
                                "outcome_id": outcome["id"], "admission_id": adm["id"], "permission_id": permission["id"],
                                "policy_version": permission["policy_version"], "purpose": purpose,
                                "rights_reference": adm["rights_reference"], "reviewer": adm["reviewer"],
                                "source_scopes": json.loads(adm["source_scopes"]),
                                "valid_until": min(adm["expires"], permission["expires"], private["expires"], drow["expires"], orow["expires"])})
            identifier = uuid.uuid4().hex
            rows.sort(key=lambda item: (item["decided_at"], item["id"]))
            data_sha = c.digest(rows)
            manifest = {"schema": "financial-evidence.learning-snapshot.v1", "id": identifier,
                        "purpose": purpose, "target": target, "as_of": cutoff, "created_at": now,
                        "row_count": len(rows), "data_sha256": data_sha, "lineage": lineage}
            db.execute("INSERT INTO snapshots VALUES (?,?,?,?,0)", (identifier, c.encode(manifest).decode(), c.digest(manifest), now))
            self._audit(db, now, "dataset_exported", identifier)
        return {"manifest": {key: value for key, value in manifest.items() if key != "lineage"}, "rows": rows,
                "status": "ready_for_evaluation" if rows else "insufficient_data"}

    def record_model(self, *, model_id, snapshot_id, artifact_sha256):
        c.label(model_id)
        if not isinstance(artifact_sha256, str) or not c.SHA.fullmatch(artifact_sha256):
            raise ValueError("invalid model artifact digest")
        now = self._now()
        with self.connection() as db:
            self._expire(db, now)
            snapshot = db.execute("SELECT * FROM snapshots WHERE id=?", (snapshot_id,)).fetchone()
            if snapshot is None or snapshot["invalidated"]:
                raise ValueError("snapshot missing or invalidated")
            manifest = json.loads(snapshot["manifest"])
            if c.digest(manifest) != snapshot["sha256"]:
                raise ValueError("snapshot manifest integrity mismatch")
            if not manifest["row_count"]:
                raise ValueError("empty snapshots cannot support a trained model")
            existing = db.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
            if existing:
                if existing["snapshot_id"] != snapshot_id or existing["artifact_sha256"] != artifact_sha256:
                    raise ValueError("model id already binds different content")
            else:
                db.execute("INSERT INTO models VALUES (?,?,?,?,0)", (model_id, snapshot_id, artifact_sha256, now))
        return {"model_id": model_id, "snapshot_id": snapshot_id, "needs_review": False,
                "created": existing is None, "commercial_release_authorized": False}

    def validate_snapshot(self, dataset):
        """Recheck current permission state before any supported local evaluation."""
        if not isinstance(dataset, dict) or not isinstance(dataset.get("manifest"), dict) or not isinstance(dataset.get("rows"), list):
            raise ValueError("invalid snapshot export")
        now = self._now()
        with self.connection() as db:
            self._expire(db, now)
            row = db.execute("SELECT * FROM snapshots WHERE id=?", (dataset["manifest"].get("id"),)).fetchone()
            if row is None or row["invalidated"]:
                raise ValueError("snapshot missing or invalidated by expiry/withdrawal")
            manifest = json.loads(row["manifest"])
            if (c.digest(manifest) != row["sha256"] or dataset["manifest"] != {key: value for key, value in manifest.items() if key != "lineage"}
                    or c.digest(dataset["rows"]) != manifest["data_sha256"]):
                raise ValueError("snapshot content integrity mismatch")
        return {"snapshot_id": manifest["id"], "currently_valid": True, "checked_at": now}

    def _invalidate(self, db, *, tenant=None, now=None):
        for row in db.execute("SELECT id,manifest FROM snapshots WHERE invalidated=0").fetchall():
            lineage = json.loads(row["manifest"])["lineage"]
            if any((tenant is not None and item["tenant"] == tenant) or (now is not None and item["valid_until"] <= now) for item in lineage):
                db.execute("UPDATE snapshots SET invalidated=1 WHERE id=?", (row["id"],))
                db.execute("UPDATE models SET needs_review=1 WHERE snapshot_id=?", (row["id"],))

    def _expire(self, db, now):
        self._invalidate(db, now=now)
        db.execute("UPDATE permissions SET status='expired' WHERE status='active' AND expires<=?", (now,))
        removed = db.execute("DELETE FROM records WHERE expires<=?", (now,)).rowcount
        db.execute("DELETE FROM outcome_reviews WHERE NOT EXISTS (SELECT 1 FROM records r WHERE r.tenant=outcome_reviews.tenant AND r.kind='outcome' AND r.id=outcome_reviews.outcome_id)")
        db.execute("DELETE FROM admissions WHERE expires<=? OR NOT EXISTS (SELECT 1 FROM records r WHERE r.tenant=admissions.tenant AND r.kind='decision' AND r.id=admissions.decision_id)", (now,))
        return removed

    def expire(self):
        now = self._now()
        with self.connection() as db:
            return {"expired_records_deleted": self._expire(db, now), "as_of": now}

    def withdraw(self, credential, *, purposes=None, delete=False):
        now = self._now()
        if purposes is not None and (not isinstance(purposes, list) or not purposes or set(purposes) - c.PURPOSES):
            raise ValueError("invalid withdrawal purposes")
        with self.connection() as db:
            tenant = self._tenant(db, credential)
            selected = set(purposes or c.PURPOSES)
            if "private_evidence" in selected:
                selected.update(c.TRAINING)
            for purpose in selected:
                db.execute("UPDATE permissions SET status='withdrawn' WHERE tenant=? AND purpose=?", (tenant["id"], purpose))
            if selected & c.TRAINING:
                self._invalidate(db, tenant=tenant["id"])
                for purpose in selected & c.TRAINING:
                    db.execute("DELETE FROM admissions WHERE tenant=? AND purpose=?", (tenant["id"], purpose))
            deleted = 0
            if delete:
                kinds = {"tool"} if selected == {"measurement"} else ({"decision", "outcome"} if "private_evidence" in selected and "measurement" not in selected else {"tool", "decision", "outcome"} if "private_evidence" in selected else set())
                for kind in kinds:
                    deleted += db.execute("DELETE FROM records WHERE tenant=? AND kind=?", (tenant["id"], kind)).rowcount
                if "outcome" in kinds:
                    db.execute("DELETE FROM outcome_reviews WHERE tenant=?", (tenant["id"],))
            self._audit(db, now, "permission_withdrawn", tenant["id"])
            models = [row["id"] for row in db.execute("SELECT m.id,s.manifest FROM models m JOIN snapshots s ON s.id=m.snapshot_id WHERE m.needs_review=1")
                      if any(item["tenant"] == tenant["id"] for item in json.loads(row["manifest"])["lineage"])]
        return {"withdrawn": sorted(selected), "deleted_records": deleted, "model_review_required": bool(models),
                "previously_exported_copies_and_trained_weights_require_operator_review": True}

    def delete_tenant(self, credential):
        now = self._now()
        with self.connection() as db:
            tenant = self._tenant(db, credential)
            self._invalidate(db, tenant=tenant["id"])
            for table in ("admissions", "outcome_reviews"):
                db.execute(f"DELETE FROM {table} WHERE tenant=?", (tenant["id"],))
            db.execute("DELETE FROM tenants WHERE id=?", (tenant["id"],))
            self._audit(db, now, "tenant_deleted", hashlib.sha256(tenant["id"].encode()).hexdigest())
        return {"deleted": True, "lineage_retained_without_record_contents": True,
                "previously_exported_copies_and_trained_weights_require_operator_review": True}

    def model_lineage(self):
        with self.connection() as db:
            self._expire(db, self._now())
            return [dict(row) for row in db.execute("SELECT * FROM models ORDER BY created,id")]

    def report(self, credential=None):
        """Private/operator report. HTTP always passes the caller's credential."""
        now = self._now()
        with self.connection() as db:
            self._expire(db, now)
            tenant = self._tenant(db, credential) if credential is not None else None
            query = "SELECT tenant,body FROM records WHERE kind='tool'"
            rows = db.execute(query + (" AND tenant=?" if tenant is not None else ""), (tenant["id"],) if tenant is not None else ()).fetchall()
            events = [(row["tenant"], json.loads(row["body"])) for row in rows]
            tenants = db.execute("SELECT id,organisation_verified FROM tenants" + (" WHERE id=?" if tenant is not None else ""), (tenant["id"],) if tenant is not None else ()).fetchall()
            scope = " AND tenant=?" if tenant is not None else ""
            parameters = (tenant["id"],) if tenant is not None else ()
            decisions = db.execute("SELECT count(*) FROM records WHERE kind='decision'" + scope, parameters).fetchone()[0]
            outcomes = db.execute("SELECT count(*) FROM records WHERE kind='outcome'" + scope, parameters).fetchone()[0]
            verified = db.execute("SELECT count(*) FROM outcome_reviews WHERE 1=1" + scope, parameters).fetchone()[0]
        from .insights import confirmed_workflows, summarize
        operational = [event for _, event in events if not c.is_feedback(event)]
        modes = Counter(event["mode"] for event in operational)
        useful = confirmed_workflows(events)
        histories = {}
        for owner, event in useful:
            histories.setdefault(owner, []).append(event["occurred_at"])
        retention = {}
        for name, start, end in (("d7", 7, 14), ("d30", 30, 37)):
            eligible = [times for times in histories.values() if min(times) + end * DAY <= now]
            returned = sum(any(min(times) + start * DAY <= at < min(times) + end * DAY for at in times) for times in eligible)
            retention[name] = {"returned": returned, "eligible": len(eligible), "rate": returned / len(eligible) if eligible else None,
                               "window_days": [start, end], "cohort": "tenant first confirmed useful shadow/paper/operator-reported production completion"}
        durations = sorted(event["duration_ms"] for event in operational)
        costs = [event["cost_usd"] for event in operational if "cost_usd" in event]
        useful_ids = {(owner, event["product"], event["task"], event["mode"],
                       event.get("logical_workflow_id", event["id"])) for owner, event in useful}
        eligible_cost_events = [event for event in operational if event["mode"] in {"shadow", "paper", "operator_reported_production"}]
        useful_costs = [event["cost_usd"] for event in eligible_cost_events if "cost_usd" in event]
        daily_cost = {}
        for event in operational:
            day = datetime.fromtimestamp(event["occurred_at"], timezone.utc).date().isoformat()
            bucket = daily_cost.setdefault(day, {"known_cost_usd": 0, "observed_requests": 0, "eligible_requests": 0})
            bucket["eligible_requests"] += 1
            if "cost_usd" in event:
                bucket["known_cost_usd"] += event["cost_usd"]
                bucket["observed_requests"] += 1
        return {"as_of": now, "coverage": "explicitly enrolled submissions only; absent measurements are unknown",
                "requests": len(operational), "by_mode": dict(sorted(modes.items())),
                "measurement_records": len(events),
                "feedback_records": len(events) - len(operational),
                "product_learning": summarize(events),
                "by_product_tool": dict(sorted(Counter(event["product"] + ":" + event["tool"] for event in operational).items())),
                "errors": sum(event["status"] == "error" for event in operational),
                "refused": sum(event["status"] == "refused" for event in operational), "stale": sum(event["status"] == "stale" for event in operational),
                "p95_duration_ms": durations[min(len(durations) - 1, int(len(durations) * .95))] if durations else None,
                "p50_duration_ms": durations[min(len(durations) - 1, int(len(durations) * .50))] if durations else None,
                "max_duration_ms": durations[-1] if durations else None,
                "cache_hits": sum(event.get("cached") is True for event in operational),
                "confirmed_useful_workflows": len(useful_ids), "usefulness_is_operator_reported": True,
                "enrolled_tenants": len(tenants), "verified_organisation_workspaces": sum(row["organisation_verified"] for row in tenants),
                "distinct_organisations": None,
                "retention": retention, "known_cost_usd": sum(costs), "cost_observed_requests": len(costs),
                "cost_eligible_requests": len(operational), "cost_by_utc_day": dict(sorted(daily_cost.items())),
                "cost_per_useful_workflow_usd": sum(useful_costs) / len(useful_ids) if useful_ids and len(useful_costs) == len(eligible_cost_events) else None,
                "cost_per_useful_workflow_scope": "all measured shadow/paper/operator-reported production requests, excluding tests/backtests/unknown",
                "outcome_coverage": {"decisions": decisions, "linked_outcomes": outcomes, "reviewer_verified_outcomes": verified,
                                     "linked_rate": outcomes / decisions if decisions else None, "verified_rate": verified / decisions if decisions else None},
                "cost_is_operator_reported": True, "no_inference_of_people_trades_positions_or_preferences": True}
