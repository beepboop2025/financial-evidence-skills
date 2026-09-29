#!/usr/bin/env python3
"""Read only a bounded ledger member from this workflow's last retained artifact."""

import io
import json
import os
import subprocess
import zipfile
from pathlib import Path

REPO = "beepboop2025/financial-evidence-skills"


def api(route):
    return subprocess.check_output(
        ["gh", "api", "repos/" + REPO + "/" + route], timeout=60
    )


def main():
    directory = Path("reliability-evidence")
    directory.mkdir(exist_ok=True)
    artifacts = json.loads(
        api("actions/artifacts?name=funding-reliability-ledger&per_page=20")
    )["artifacts"]
    candidates = [
        a
        for a in artifacts
        if not a["expired"]
        and str(a["workflow_run"]["id"]) != os.environ["GITHUB_RUN_ID"]
        and a["workflow_run"]["head_branch"] == "main"
    ]
    for artifact in sorted(candidates, key=lambda a: a["created_at"], reverse=True):
        run = json.loads(api("actions/runs/" + str(artifact["workflow_run"]["id"])))
        if run.get("path") != ".github/workflows/funding-reliability.yml" or run.get(
            "event"
        ) not in ("schedule", "workflow_dispatch"):
            continue
        if artifact["size_in_bytes"] > 32 * 1024 * 1024:
            raise ValueError("oversized ledger archive")
        raw = api("actions/artifacts/" + str(artifact["id"]) + "/zip")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            matches = [i for i in archive.infolist() if i.filename == "ledger.json"]
            if len(matches) != 1 or matches[0].file_size > 64 * 1024 * 1024:
                raise ValueError("missing or oversized ledger")
            data = archive.read(matches[0])
        (directory / "ledger.json").write_bytes(data)
        (directory / "continuation.json").write_text(
            json.dumps(
                {
                    "previous_artifact_id": artifact["id"],
                    "previous_run_id": run["id"],
                    "history_reset": False,
                }
            )
            + "\n"
        )
        return
    (directory / "continuation.json").write_text(
        json.dumps(
            {
                "previous_artifact_id": None,
                "history_reset": True,
                "reason": "no_retained_prior_workflow_artifact",
            }
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
