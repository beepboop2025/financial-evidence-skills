# Public source-rights projection (2026-10-28)

This engineering policy is not a legal opinion, a blanket data license, or an
attestation that every public product route has completed a rights review.

## Reviewed Financial Evidence paths

The capital-market packet and table withhold current FRED-sourced VIX and ICE
BofA high-yield OAS observations, the dependent funding/TELL readings, and the
FRED-dependent official-bid block. The money-market packet and table withhold
FRED-tagged observations and histories plus their dependent market narratives
and policy-spread readings. Identity, source URLs, observation dates, units,
restriction reasons and terms links remain visible. Calling a number derived
does not itself establish permission to redistribute it.

This follows the source-specific permission gap documented at:
- https://fred.stlouisfed.org/legal/terms/
- https://fred.stlouisfed.org/series/BAMLH0A0HYM2
- https://fred.stlouisfed.org/series/VIXCLS

FRED's current terms include separate MCP Connector terms; this policy does
not assert that all AI use is forbidden. ICE's series notice and the VIX
citation notice are different conditions. No written permission covering the
current hosted redistribution was established in this review.

The filter runs on source fetches, and again on table projection so an older
upstream or cached packet cannot bypass it. Unexpected root types, schemas or
required payload shapes on these reviewed routes fail closed to unavailable
metadata rather than returning an unreviewed document. Unrelated sources are unchanged.
Original acquired response hashes remain acquisition receipts. When the
returned document changes, publication_projection declares that it is a
projection and gives a separate SHA-256 over canonical returned JSON. No
FRED capture is relabelled as an original-publisher capture.

The legacy Workspace funding-review archive also contains five explicitly
FRED-attributed inputs. Its shared JSON/CSV read boundary now withholds those
values after verifying original captured bytes, retains the four other rows,
sets ready=false and redistribution_restricted, and qualifies historical
ready_probes as capture-time operational metrics. CSV downloads contain blank
restricted values and restricted states, with a separate projection hash.
Immutable captured files, original manifest hashes and input hashes are not
rewritten. The separately operated institutional original-publisher acquisition
path is distinct; independently acquired, qualified values are not relabelled
FRED copies and are not blanket withheld. China metadata-only restrictions
remain in force. No customer-license or private-data feature is introduced.

## Reachable Financial Evidence tool paths

The nine Workspace tools use these boundaries: query, sources and agent_query
use the service table projection; review builds its sections through the same
table projection; packet uses the filtered source fetch; funding workflow uses
EvidenceAgentClient.query and the same table projection. Datasets and route
return metadata only. Funding_review uses the verified archive JSON/CSV
projection; its actual five FRED source labels cannot bypass the policy. The legacy stdio financial_evidence_fetch tool is
not one of the nine Workspace tools, but it also uses the filtered source fetch.

The HTTP MCP regression enumerates all nine actual registered tool names and
calls each one with a sentinel upstream fixture. It also covers the funding
REST route and legacy fetch, and verifies that a withheld USD benchmark cannot
produce prepared_response=true. A separate actual-capture-shaped regression
exercises funding_review through MCP, REST and CSV, verifies projection hashes,
and proves original artifact bytes remain unchanged. Neither substitutes a mock filter.

## Limits and release acceptance

The Seiche US pack separately marks fred_daily/fred_weekly metadata-only;
direct NYFed and Treasury adapters retain their existing policy. Current
policy must be checked at read time even for previously stored rows.

This patch does not claim rights approval for other Seiche endpoints,
prebuilt market payloads, native FX/Estuary tools, or all third-party data in the
fleet. Review those source paths separately before broader attestations.

Before activation, verify the exact deployed source revision, run packet and
table regression tests, restart the owning service to drop old process
caches, then read back public packets and tables. Confirm withheld values
and histories remain absent, original-source values remain correctly
labelled, and dates/rights/projection hashes survive. Provider SUCCESS alone
is not evidence of those public outputs.

## Follow-up: saved FX and auction funding narratives

The fixed Financial Evidence `forex` topic retrieves
`/api/v2/world-markets?section=forex`. Its saved FX/materials engines use FRED
inputs without a per-field redistribution qualification. This route now returns
metadata only, including the original acquisition receipt and a separate public
projection hash. Unexpected schemas fail closed. Duplicated top-level summaries
and newly added unreviewed fields are withheld as well as the FX payload.
The independently acquired ECB exchange-rate data on the separate `gift-city`
and `gold` routes is unchanged; it is not relabelled as the saved FX source.

The capital-market reportcard's `letter_line` can quote FRED SOFR–IORB spreads
and reserve changes even though its displayed registry lists Treasury sources.
That narrative and unreviewed reportcard fields are withheld. Its Treasury-only
auction demand-fatigue statistics, observation dates, card counts and window
definition remain. The remaining Treasury auction block is unchanged.

Source trace at Seiche revision `1fa33dacc46a2c0aa2a3ff38be2995ab560748e0`:
- [assembly inputs](https://github.com/beepboop2025/seiche/blob/1fa33dacc46a2c0aa2a3ff38be2995ab560748e0/backend/seiche/assemble.py):
  reportcard funding inputs around lines 846–850; FX/materials assembly around
  line 941.
- [reportcard computation](https://github.com/beepboop2025/seiche/blob/1fa33dacc46a2c0aa2a3ff38be2995ab560748e0/backend/seiche/engines/reportcard.py):
  `_fatigue_rows` uses auction indirect shares; the letter around line 430
  combines auction results with funding event studies.
- [world section projection](https://github.com/beepboop2025/seiche/blob/1fa33dacc46a2c0aa2a3ff38be2995ab560748e0/backend/seiche/markets/world.py)
  routes those saved engine outputs into the public sections.

The current nine-tool Workspace MCP schema does not accept the forex topic.
The REST packet route and the legacy stdio fetch schema do. Actual HTTP/legacy
dispatch tests cover those reachable paths without expanding the tool schema.
This remains a bounded route policy, not an attestation for all native Seiche
tools or a new private-source integration.
