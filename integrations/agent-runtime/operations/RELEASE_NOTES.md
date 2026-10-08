Runtime Operations 1.0.3 closes disaster-recovery and source-diagnosis gaps around the unchanged Financial Evidence 0.1.7 runtime.

- Schedule backups at fixed UTC quarter-hours with persistent missed-run catch-up, removing startup-relative triggers that rearmed during shared-host service-manager reloads.
- Discover candidate encrypted snapshots when host-local receipts are lost, with an explicit distinction between a listing and restore verification.
- Restore an exact snapshot using the independently retained configuration and repository credentials, without the original research or operations directories.
- Validate repository, installation, runtime, workflow, payload, receipt and retry-key identities before publishing a stopped copy and reconstructed receipt.
- Publish the recovered database only after its stopped state is durable, including when recovery is interrupted.
- Explain retained source blocks with affected-row counts, representative fields and remediation guidance in the private console and diagnostics endpoint.
- Replace malformed prior monitor state with an explicit critical incident and a new bounded report.
- Verify all seven existing unit hashes against the prior applied installation plan before upgrading, including legacy monitor units; refuse unrecognized, missing, modified or symlinked units.
- Restart the read-only console on upgrade so it adopts the new release; preserve rollback to the prior owned console.

Acceptance includes real encrypted Restic recovery with both original state paths inaccessible, preserved retry keys, a stopped replacement and unchanged repository snapshot inventory. Operations 1.0.0 snapshots remain readable. Runtime policies, source rights and execution authority are unchanged. No automatic snapshot selection, source repair, broker action or customer telemetry is added.
