# Research Desk measurement

The [browser desk](https://beepboop2025.github.io/financial-evidence-skills/start/)
reduces first-use friction for LiquiLens, Seiche and Undertow. It does not prove
that more visitors become repeat users. Measure that outcome before scaling a channel.

## What the counters mean

| Measure | Evidence | Limitation |
| --- | --- | --- |
| Reach | Existing site and marketplace analytics | Visits and impressions are not active people. |
| Prepared research response | Server validates a nonempty, transport-complete table with at least one published numeric value | Does not establish delivery, task completion, freshness or research value. |
| Active installation | Optional key used for a prepared response in the last 30 UTC dates | A browser or client installation is not a person; one person may have several. |
| Return installation | Same key used on two different dates in that window | Automation can return too. |
| D7 / D30 return | Same key returns on that exact UTC day after its first eligible response | No rate before a complete eligible observation window. |
| Verified analyst / organization | Consenting participant plus reviewed independent ownership and a completed task | Requires evidence outside anonymous traffic. |
| Paid customer | Verified bank credit and linked commercial agreement | Payment-form submission is not payment. |

The desk sends **no separate click or download telemetry**. Anonymous query
counts store only day, traffic class, outcome and a bounded count. Optional keys
attribute ordinary query responses. Page loads, source-health checks, empty
matches and rows containing only unavailable values cannot start a research cohort.
The server deduplicates the same installation/day/response/class. Different
filters or source revisions can produce different responses.

Enrollment is off by default. It is not an account, quota upgrade or access key.
All enrolled installations start unverified. Operator checks set
`X-Liquilens-Traffic-Class: synthetic`; the browser uses `?operator=1` to disable
visitor enrollment and mark research requests. Self-reported labels cannot prove
independence. The existing local ownership-review command can classify future
activity; it never retroactively relabels past events.

## Read the private scorecard

On the service host, without sending a message:

```sh
docker exec financial-evidence-workspace python -m financial_evidence.workspace_usage report --directory /data/usage
```

The result separates unverified, internal, synthetic and reviewed external
installations. `monthly_active_people` and `paying_customers` stay null: this
store cannot verify either. It covers the Workspace REST query endpoint only,
not all family sites, MCP traffic, or external marketplace usage.

Storage lives separately at `/var/lib/financial-evidence-workspace/usage`.
Completions and aggregates expire after 90 UTC dates; inactive keys and cohorts
after 180 days. Browser enrollment stops after 30 days without renewed consent.
The daily `financial-evidence-workspace-usage-expiry.timer` purges records even
without requests. The mount is excluded from evidence backups. Deletion revokes
the key and removes linked events/cohorts; anonymous aggregates remain.

Limits: 100 enrollments per UTC day, 10,000 retained installations, 50,000
deduplicated response records per day and 1,000,000 aggregate counts per class
and day. Saturation and outages are not proof of non-use. Review capacity from
observed independent demand before raising limits; the current deployment is
not certified for one million active people.

## Growth decisions

The working target is one million monthly people using the products. It remains
a target, not a projection. Start with the proposed 10-analyst, three-organization
pilot and retain evidence of tasks completed and later return use. Before expanding
a channel, establish useful first tasks, repeat behavior and acceptable failure
rates for that channel. Keep paid acquisition disabled until a budget and a
measurable conversion goal exist.

Use the bank, funding and liquidity entry links below in approved placements.
The query remains editable, and opening a link does not make an API call until
the visitor runs the research. Share actions strip credentials and operator flags.

- Bank disclosures: [ESAF research](https://beepboop2025.github.io/financial-evidence-skills/start/?dataset=bank_risk&entity=ESAF&utm_source=research_kit&utm_medium=owned)
- Funding: [USD benchmarks](https://beepboop2025.github.io/financial-evidence-skills/start/?dataset=money_markets&entity=USD&utm_source=research_kit&utm_medium=owned)
- Liquidity: [Market evidence](https://beepboop2025.github.io/financial-evidence-skills/start/?dataset=market_liquidity&utm_source=research_kit&utm_medium=owned)

Campaign parameters describe the link. The private installation store does not
collect referrers or arbitrary campaign strings, so channel conversion attribution
remains incomplete. Directory acceptance, independent platform pilots and real
customer demand remain separate external outcomes.
