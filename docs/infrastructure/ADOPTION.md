# Evaluating a recurring research integration

The infrastructure objective is to make recurring financial research easy to
integrate, inspect and recover. Universal AI-trading adoption and investment
performance cannot be established by shipping this code.

## Product benefit and measurable workflows

| Product | Recurring job enabled here | Evidence of useful adoption |
|---|---|---|
| Seiche | Funding conditions / money-market research | Independently identified analyst or application returns to the workflow and can explain the resulting research use |
| LiquiLens | Covered-bank evidence review | An outside user completes a repeat review using cited bank observations |
| Undertow | Market-liquidity evidence checks | An outside application consumes a retained result with source clocks and limitations intact |
| Wider family | Existing source-health metadata | An operator catches and resolves an actual coverage/freshness issue |
| Combined products | Three-section research review | The same outside workflow uses more than one product while preserving their separate units and dates |

Source-health coverage follows the existing route registry. It does not add
unsupported product datasets or make every family product equally suitable for
trading research. No combined numerical score is produced.

## Adoption funnel and required proof

| Stage | Record | What it can establish |
|---|---|---|
| Discovery | Package/listing/page statistics | Reach; downloads can include bots and CI |
| Installation | Successful offline acceptance on another operator's machine | Integration works there; identity still requires corroboration |
| Activation | Identified external workflow obtains and uses its first usable result | First real use, after excluding internal/synthetic activity |
| Repetition | Same external installation completes useful work in multiple weeks | Retention within the stated observation window |
| Depth | Identified workflow uses multiple datasets/products | Product expansion, with an explicit denominator |
| Payment | Account entitlement plus settled/reconciled payment | Paying adoption; an API call alone cannot establish it |
| Reliability | Source-response success, blocked reasons, recovery receipts | Operational quality within measured coverage |

Local metrics supply operational run counts and owner-reported outcomes.
They deliberately leave external users, retention, paid customers and revenue
unknown. Do not add synthetic acceptance or internal live probes to an external
traction numerator. Request headers make those probes distinguishable but are
not trustworthy evidence of an outside customer by themselves.

## Integration handoff

The execution owner can consume `runtime.bundle(run_id)` and retain its SHA-256
with the existing paper/simulation decision. Required integration cases:

- Passed configured research requirements, while execution remains separately gated.
- Stale, unavailable, restricted and empty evidence, each with visible reasons.
- Identical source revision on a later run whose age policy now blocks it.
- Client timeout/retry using the same key, without a second research admission.
- Restored research journal, preserving run IDs and immutable policy.

The runtime is ready for this adapter integration when its candidate checks pass.
A downstream integration is complete only after the combined test is run against
the execution owner's actual implementation. Local runtime tests do not claim it.
