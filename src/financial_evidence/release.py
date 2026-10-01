"""Identity of the independently deployed Workspace service.

The original package and three-tool MCP keep their existing version contract.
A hosted Workspace release additionally identifies the exact source revision.
"""

import os
import re

from . import __version__

WORKSPACE_VERSION = "1.1.1"


def release_identity() -> dict:
    revision = os.getenv("FINANCIAL_EVIDENCE_SOURCE_COMMIT", "")
    if revision and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("FINANCIAL_EVIDENCE_SOURCE_COMMIT must be a full Git SHA")
    return {
        "schema": "financial-evidence.workspace-release.v1",
        "release_id": f"workspace-{WORKSPACE_VERSION}+{revision[:12]}"
        if revision
        else "unversioned-local",
        "workspace_version": WORKSPACE_VERSION,
        "package_version": __version__,
        "source_commit": revision or None,
        "contract": "financial-evidence.workspace.v1",
        "source_repository": "https://github.com/beepboop2025/financial-evidence-skills",
        "identity_scope": "operator_supplied_build_revision",
        "institutional_readiness": "not_certified",
    }
