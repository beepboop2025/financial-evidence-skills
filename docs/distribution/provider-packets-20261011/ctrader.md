# cTrader — Seiche reference-FX web-plugin candidate

Prepared 11 October 2026 IST. State: **companion ready native validation required**. No new application, agreement or message was sent by this preparation work.

## Proposed recurring use

A trader opens a compact panel alongside their workspace, fetches ten recent published EUR reference observations and retains a note with source dates. The data is macro reference context; it is not the broker's live FX/CFD price.

## Entry and prepared fields

Official entry: https://help.ctrader.com/plugins/developers/all-apps/build-a-plugin/

- Name: Seiche Reference FX.
- Description: Review dated ECB EUR reference observations for USD, GBP, JPY and INR, with units and source notices, then save a research note.
- Candidate URL after public deployment: https://beepboop2025.github.io/financial-evidence-skills/platforms/desktop/.
- Placement proposal: separate window or Trade Watch tab, large size; confirm readability in the actual client.
- Source files: integrations/finance-desktop/index.html, panel.css, panel.mjs, reference-fx.mjs.
- Data access: manual public CSV reads only; no account, quote or order SDK calls.

Publisher: **LIQUILENS PRIVATE LIMITED**. Brand: **LiquiLens**. Contact: **mrinal@liquilens.in**. Website: https://liquilens.in/.

Public demonstration: https://beepboop2025.github.io/financial-evidence-skills/start/.
Research MCP: https://api.seiche.info/openbb/mcp.
[Privacy](https://beepboop2025.github.io/financial-evidence-skills/privacy/) · [Terms](https://beepboop2025.github.io/financial-evidence-skills/terms/) · [Support](https://beepboop2025.github.io/financial-evidence-skills/support/).

The downloadable sample is limited to four ECB EUR reference-FX series. Broader LiquiLens institution and Undertow liquidity tools are separate source-bound research services. No dataset sample grants rights over unrelated sources. Customer counts, revenue, certifications, SLA commitments and named reference clients are not established by this packet.

## Remaining gate

Native in-app URL build, plugin policy declarations, actual client rendering/CORS/download tests, seller eligibility and Store review. A working standalone browser page is not a verified cTrader plugin. The panel currently uses no host SDK; confirm acceptance of a standalone URL panel or add only the minimal documented handshake if the native builder requires it.

Current cTrader documentation supports web plugins across desktop, web and mobile, with the builder in Web/Windows/Mac. Prepare a 300×300 owned logo and the hosted URL. Cross-domain links explicitly open a new tab. Do not use the SDK trading example wholesale: it includes order and position mutations unrelated to this companion.

## Evaluation assets

[Dataset factsheet](dataset-factsheet.md) · [80-row CSV sample](reference-fx-sample.csv) · [JSON sample](reference-fx-sample.json) · [Sample verification](sample-verification.json) · [Reference-FX review](sample-report-fx.md) · [Coverage and vintage review](sample-report-coverage.md).

A useful first evaluation is one dated note retained by an independent analyst. A second-day return and the analyst's assessment of usefulness are tracked separately from a successful request or an accepted listing.

## Official requirements checked

- https://help.ctrader.com/plugins/developers/all-apps/
- https://help.ctrader.com/plugins/developers/all-apps/build-a-plugin/
- https://help.ctrader.com/ctrader-store/how-tos/publish-a-product/
