# Financial Evidence semantic contract

This contract applies to Financial Evidence v0.1.5. The packet schema identifier
remains `liquidity-lab.financial-evidence-packet.v1` because v0.1.5 is an
additive compatibility release: existing fields, `status` values, source
documents, and process exit codes are retained.

The exported three-argument `Source(product, url, evidence_class)` constructor
also remains valid. Its new `human_scope_url` field defaults to an empty,
explicitly unreported value for legacy callers; built-in routes always provide
their reviewed HTTPS scope URL.

## Packet status

`status` reports only whether the fixed HTTPS retrievals succeeded:

| `status` | Meaning | CLI exit code |
|---|---|---:|
| `complete` | Every requested source was retrieved and parsed as bounded JSON. | 0 |
| `partial` | At least one, but not every, requested source was retrieved. | 1 |
| `unavailable` | No requested source was retrieved successfully. | 2 |

Every packet also carries these mandatory guardrails:

```json
{
  "transport_status": "complete",
  "status_semantics": "transport_only",
  "evidence_status": "not_evaluated",
  "carrier_verification": "not_performed"
}
```

`transport_status` must equal the legacy `status`. Neither field says that the
document is fresh, eligible, licensed for redistribution, analytically valid,
or a verified LiquiLens Evidence Carrier.

## Fixed-route metadata

Every fixed route declares `human_scope_url`, `financial_authority: "none"`,
and `carrier_state: "not_published"`. A route in that carrier state must not
contain a `carrier_url` key. An absent Carrier endpoint is represented by the
state, not by a null or placeholder URL that could be mistaken for an advertised
endpoint.

## Source-reported metadata

A successful source includes `source_reported`. Endpoint-specific adapters read
only explicitly allowlisted scalar paths. They never recursively discover
status-like fields and never infer freshness, evidence eligibility, or rights.

`state` and `clocks` are either `not_reported` or lists of records shaped as:

```json
{
  "name": "generated_at",
  "value": "2026-08-25T19:35:45Z",
  "path": "/generated_at",
  "provenance": {
    "kind": "source_document",
    "source_url": "https://api.seiche.info/api/v2/money-markets",
    "content_sha256": "sha256:..."
  }
}
```

`path` is an RFC 6901 JSON Pointer into the returned `document`. The provenance
hash identifies the exact fetched bytes. `not_reported` means that no configured,
non-null scalar was present; it is not a negative evidence judgment.

## Retrieval security

The v0.1.5 guardrail does not broaden network access. Retrieval remains limited
to the fixed public HTTPS route allowlist, redirects are rejected before they
are followed, accepted content must be JSON, and response bytes remain bounded
by the existing configurable limit (maximum 4 MiB).

## OpenBB table projections (separately versioned Workspace service)

The optional OpenBB Workspace backend projects explicitly selected public fields
into typed rows. A numeric row retains its source URL, JSON pointer, native unit,
observation date, retrieval time and fetched-byte SHA-256. It does not grant
financial authority, infer freshness, verify an Evidence Carrier, reconstruct a
withheld percentile or combine products into a score. Metadata-only China rows
have no numeric economic value or observation date.

Per-row `availability` describes the projection or repeats publisher metadata;
it is separate from `transport_status`. A successful HTTP response whose expected
collection is missing produces a `schema_unavailable` diagnostic. Query filters
and pagination never remove source failures from the response's `diagnostics`
and `sources` metadata. A cache hit retains the original retrieval and publisher
clocks and separately reports cache age. Expired successful responses are not
used as fallback after an upstream failure.

The Workspace backend has a separate six-tool MCP surface. The original stdio and
public v0.1.5 MCP tool contract remain three tools. Source-tree additions do not
assert that existing published artifacts or deployed services have been upgraded.

Explicit `prohibited` and `metadata_only` restrictions suppress numeric table
values even when a child reports availability. `derived_only` also suppresses
raw benchmark rates, their history, and raw capital-market prices: changing a
number's table shape does not create a derived work. Already published derived
bank diagnostics and liquidity percentiles retain their existing restriction
checks. Absence of a restriction is not an independent licence verification.

## USD funding review checks (Workspace 1.0.1, policy v3)

`scripts/check_funding_review.py` assesses captured USD desk, global atlas,
health and optional desk-history documents. It requires nine named observations
with expected units and source dates, checks snapshot age separately, and joins
each supported NY Fed observation to its own canonical atlas series. Missing
data, duplicates, restrictions, conflicting values and missed publication
opportunities require attention.

Daily SOFR and EFFR clocks use an independently reviewed 2026 NY Fed calendar,
including rate-specific exceptional closure days. An atlas deadline must match
that calendar exactly; an arbitrary future deadline cannot excuse aging data.
Dates outside the reviewed calendar fail closed. The bounded January 2027
bridge supports the final 2026 observations and does not certify the 2027 year.
Treasury freshness uses the documented publication schedule separately.

The desk deliberately clips its inputs to the latest exact-date SOFR-IORB
intersection. A validated own-series historical point may support that dated
review; it does not make the observation the latest value for that instrument.
REST, MCP and every saved CSV retain `review_asof`, `review_scope`,
`latest_per_instrument`, `canonical_latest_asof` and
`newer_observation_available`. Missing or contradictory historical proof cannot
qualify aging inputs. Original publisher labels and source clocks are retained.

Live readers require the capture's complete release identity to match the
running backend, verify the report and CSV hashes, and withhold ready exports
after failure, expiry or mismatch. Offline replay uses the original capture's
implementation and is explicitly separate from current readiness. Passing
checks does not establish as-published historical vintages, an SLA, financial
authority or institutional production readiness.
