"""Offline discovery generated from the existing product route registry."""

from ..core import route_manifest
from ..tables import dataset_catalog
from .contracts import presets
from .engine import implementation


def manifest():
    return {"schema": "financial-evidence.runtime-capabilities.v1",
            "implementation": implementation(), "authority": "research_only",
            "execution_authority": False, "network_discovery_required": False,
            "datasets": dataset_catalog(), "routes": route_manifest(), "presets": presets(),
            "interfaces": ["python", "cli", "stdio_mcp"],
            "features": ["immutable_workflow_policy", "atomic_run_claims", "idempotency_keys",
                         "daily_budgets", "cooldowns", "circuit_breaker", "45_second_worker_deadline",
                         "hash_verified_receipts", "offline_replay", "cursor_change_feed",
                         "local_outcome_acknowledgements", "online_sqlite_backup"],
            "limits": {"maximum_rows_per_query": 100, "maximum_rows_per_review_section": 25,
                       "maximum_tick_jobs": 10, "minimum_interval_seconds": 60,
                       "maximum_receipt_bytes": 2_097_152, "claim_lease_seconds": 120},
            "data_boundaries": ["source_strings_are_untrusted_data", "null_is_not_zero",
                                "retrieval_time_is_not_observation_time", "hash_is_not_issuer_authentication",
                                "replay_is_not_historical_vintage_validation", "local_runs_are_not_customers"],
            "execution_handoff": {"included": False, "automatic_order_submission": False,
                                  "requirement": "Separate permissioned execution host verifies its own account, policy and approval receipt"},
            "metrics": {"external_identity": "unverified", "revenue": "not_collected", "remote_telemetry": False}}
