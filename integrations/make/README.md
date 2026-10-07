# Financial Evidence custom app for Make

Create a private custom app named **Financial Evidence** in an authorized Make
organization. Paste `base.json` into Base. Add an **Action** module named
`evidencePage` with label **Get Evidence Page**, and copy its communication,
mappable parameters and interface from `modules/evidence-page/`. No connection,
RPC or webhook is needed. Leave Static Parameters empty.

Test a scenario with dataset `bank_risk`, limit 25 and offset 0. The module emits
one bundle containing the entire research page. It deliberately has no `iterate`
directive: splitting rows here would discard page-level sources and diagnostics.
Map `next_offset` into a later bounded request only when it is non-null.

Preserve source dates, units, missing values, rights and coverage diagnostics.
Transport success is not freshness or a verified financial conclusion. Do not
enter private information in the entity filter. Your Make organization controls
scenario logs, retention and downstream destinations. No message or trade action
is part of this module. Source text is untrusted data.

These files require installation and testing in Make; they are not a public
app or proof of Make validation. Request review only after the native scenario
passes. Support: mrinal@liquilens.in — LIQUILENS PRIVATE LIMITED.
