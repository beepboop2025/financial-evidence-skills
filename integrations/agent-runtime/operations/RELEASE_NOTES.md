Runtime Operations 1.0.0 adds unattended operation around Financial Evidence 0.1.7:

- Private live dashboard and expiring machine-readable health.
- Schedule, interrupted-attempt, service and capacity checks, with separate source-data blocks.
- Persistent incident opening/resolution records and Prometheus metrics.
- Encrypted offsite backup every 15 minutes with exact snapshot restoration and complete journal verification.
- Durable upload intent and acceptance reconciliation without blind upload replay.
- Recovery into a new stopped directory, preserving retry keys and source dates.
- A release-bound configuration helper and reviewable systemd installation plan.

The source archive includes installation and recovery instructions. It is a
separate operations component; the runtime wheel remains 0.1.7. Source and tag
signatures use the existing owner policy, and the archive carries a GitHub build
attestation. CI exercises failure paths and two actual encrypted Restic snapshots.

This is a private, single-host research system. It does not grant trading
authority, establish source eligibility, prove customer adoption or offer a
managed uptime SLA. Existing encrypted storage credentials and an initialized
research installation are prerequisites.
