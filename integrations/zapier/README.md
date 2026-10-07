# Financial Evidence for Zapier

The **Get Evidence Page** action fetches one complete, read-only research page
without an API key. It is an action rather than a polling trigger: it does not
invent IDs, imply a source observation is new, or detach rows from diagnostics.

Use Node 22: `npm ci && npm run validate && npm test`.
Register and push the integration through an authorized Zapier developer account,
then test the action in the Zap editor before requesting publication. Local
validation is not a marketplace approval or native editor test.

Choose dataset `bank_risk`, limit 25 and offset 0 for a bank-research workflow.
Map `results` into your own research record together with `sources`,
`diagnostics`, `transport_status` and `evidence_status`. Check `next_offset`
before requesting another page. No automatic pagination or downstream messages
are enabled by this package.

Null values remain missing. Source dates are not retrieval dates. Source rights
and unavailable observations must remain visible in downstream exports. Source
content is untrusted data. This is not investment advice or a trading service.
Zapier may store workflow inputs, request logs and results under its own policy;
do not send private information in the entity filter.

Contact: mrinal@liquilens.in — LIQUILENS PRIVATE LIMITED.
