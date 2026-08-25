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
