# Institutional integration evaluation packet

Prepared 6 October 2026. This is a technical evaluation packet, not an accepted
vendor listing or a certification. The portable notebook/client can be tested
without accessing or redistributing Bloomberg, LSEG or FactSet data.

## Proposed research application

**Financial Evidence Research Desk** brings together three separately scoped
views: LiquiLens for covered-bank evidence, Seiche for dollar funding, and
Undertow for market liquidity. The user keeps observation dates, native units,
original sources, hashes, missingness and rights labels with every result.
The tools are read-only and do not route orders or produce a universal score.

Public technical interfaces:

- OpenBB backend: `https://api.seiche.info/openbb`
- Typed API: `https://api.seiche.info/openbb/openapi.json`
- MCP: `https://api.seiche.info/openbb/mcp`
- Release identity: `https://api.seiche.info/openbb/api/v1/release`
- Source status: `https://api.seiche.info/openbb/api/v1/sources`
- FDC3 reference app: `https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/evidence-inspector/`
- Source code, issues and release history: `https://github.com/beepboop2025/financial-evidence-skills`

## Bloomberg evaluation path

Bloomberg describes BQuant Enterprise as supporting a firm's own data in its
secured research environment. An entitled administrator should decide whether
to permit outbound HTTPS to the public endpoint or import a captured CSV/JSON
through the firm's approved process. Start with `research_desk.ipynb` and
`research_client.py`; the notebook uses standard Python and does not import
Bloomberg libraries or request Bloomberg data.

For a native Terminal application or broader App Portal distribution, use the
Bloomberg developer/partner process. A portable Python example, FDC3 record or
public endpoint does not establish acceptance. Native BQuant, identity,
entitlement and App Portal testing have not been performed for this kit.

References: [BQuant](https://professional.bloomberg.com/products/bloomberg-terminal/research/bquant/),
[Enterprise Console](https://console.bloomberg.com/),
[App Portal developer overview](https://data.bloomberglp.com/professional/sites/10/Fact-Sheet-App-Portal-Overview-for-Developers.pdf).
The App Portal overview is historical; confirm current admission requirements
with Bloomberg before making a submission or signing commercial terms.

## Other institutional environments

| Environment | Asset available for evaluation | Acceptance still needed |
| --- | --- | --- |
| OpenBB Workspace | Hosted custom backend, widgets and app | Curated directory review; public PR #12 remains separate |
| Bloomberg BQuant / Terminal | Portable notebook, CSV/JSON, API schema, this packet | Entitled sandbox and administrator/vendor evaluation; native integration and App Portal acceptance |
| LSEG Workspace | Cited capture and FDC3 reference app | Supported import/context interface and any partner approval |
| FactSet | Cited capture, API contract and dataset description | Firm/vendor-approved external-data integration and distribution |
| FDC3-compatible desktop | Self-hosted AppD record and reference app | Desktop-agent compatibility, permitted contexts and directory approval |

## Evaluation checklist

1. Record the actual deployed release identity and evaluate each dataset's
   current source status. A process health check is insufficient.
2. Import a funding table, a covered-bank table and a liquidity table. Preserve
   source fields, dates, null values and source hashes in the native application.
3. Demonstrate a failed source, withheld value, empty entity match and changed
   snapshot. None should appear as zero, safe, or silently complete.
4. Review source-by-source redistribution rights. The MIT software license is
   not a blanket license for all underlying data. Do not submit restricted or
   review-held payloads as vendor-distributable samples.
5. Have the owner supply legal entity, authorized signatory, commercial terms,
   support commitments and security attestations if the vendor requires them.
   This packet does not invent these attestations or promise an SLA.
6. After acceptance, run a voluntary analyst pilot. Measure a first useful task,
   repeat use on another day, and retained use. Keep verification traffic separate.

No new vendor inquiry, submission, purchase or commitment was made by preparing
this packet. Reconcile any existing vendor correspondence before submitting.
