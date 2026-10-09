# Platform submissions and reconciliation — 10 October 2026

This record separates new submission activity from existing public listings and
account progress. It does not establish customer use, retention or payment.
The [sanitized receipts](platform-expansion-20261010.json) identify the observations
and hashes of the retained private evidence.

## New submission activity

| Destination | Recorded outcome | Remaining step |
| --- | --- | --- |
| [MCPServer.cc](https://mcpserver.cc/submit) | The Financial Evidence submission form explicitly acknowledged receipt | Editorial review and an independently verified public listing |
| [Public APIs MCP section, PR 7884](https://github.com/public-apis/public-apis/pull/7884) | One Financial Evidence MCP entry submitted; public PR readback verified | Maintainer review and resolution of the upstream MCP-format validation mismatch |
| [API Vault, issue 327](https://github.com/exa-studio/ApiVault/issues/327) | Official Add Your API issue created and exact text read back | Maintainer approval and public catalog inclusion |
| [Fintech Sandbox](https://www.fintechsandbox.org/become-a-data-partner/) | Provider enquiry explicitly acknowledged for existing public research interfaces | Qualification review; partnership and access or licensing terms are not agreed |
| [MCP Server Finder](https://mcpserverfinder.com/) | Submission email from `mrinal@liquilens.in` verified in the sender's Sent mailbox | Recipient delivery, review and listing remain unverified |

The first four have operator or repository submission receipts. The fifth is
recorded as `sent_delivery_unverified`; a sender-side receipt does not prove
recipient delivery. No paid placement was purchased.

The Fintech Sandbox enquiry is a non-binding provider qualification request for
LIQUILENS PRIVATE LIMITED. It proposes the existing public funding, institution
and liquidity research interfaces. It commits no expanded data licence,
unrestricted third-party redistribution, trial access or paid sponsorship.

Public APIs PR 7884 uses anonymous HTTP transport and the actual Glama install
listing. New-row checks, link checks and protocol discovery passed. The public
README validation failed: the unchanged upstream formatter already reports
604 diagnostics and interprets MCP Transport/Install cells as REST HTTPS/CORS.
The proposed entry adds two instances of that mismatch. Validation-package tests
passed; the PR discloses the failure and does not claim green README validation.
No financial research tool was invoked in its synthetic protocol check.

## Existing work reconciled

- **API.market:** the earlier [Seiche Reference FX offer](https://api.market/store/liquilens/seiche-reference-fx)
  is now publicly visible without authentication, including homepage discovery.
  The ledger records `live` for catalog presence. Current client-rendered checkout,
  gateway freshness, complete-history parity and paid adoption remain unverified.
  Earlier saved prices and gateway tests retain their original observation dates.
- **Datarade:** authenticated mail confirms company/provider account approval.
  The initial password-activation question remains with the account owner, so
  the state is `ready_account_action`.
  No public provider page or dataset publication is claimed.
- **MCP Market:** existing [LiquiLens](https://mcpmarket.com/server/liquilens),
  [Seiche](https://mcpmarket.com/server/seiche) and
  [Undertow](https://mcpmarket.com/server/undertow) entries were found. Each free
  submission action reported already listed. These are reconciled older placements;
  no new submission, paid placement or native-installation proof is counted.
- **LobeHub:** seven existing public search cards cover LiquiLens, Seiche,
  Undertow, Palimpsest, Riptide, NoiseFloor and Evidence Carrier. All were marked
  **Unvalidated**. The ledger records `listed_incomplete`: imported descriptions,
  tool counts, publisher verification and native compatibility are not certified.
- **Public APIs REST entries:** [LiquiLens PR 7067](https://github.com/public-apis/public-apis/pull/7067)
  was already merged and its Finance row is present. Existing
  [Seiche PR 7801](https://github.com/public-apis/public-apis/pull/7801) and
  [Undertow PR 7802](https://github.com/public-apis/public-apis/pull/7802)
  remain open. These earlier records are now explicit in the product ledger.
- **AllMCPs:** Financial Evidence's current tag pin and description are visible,
  but exact wheel-command propagation and native checks remain open. Undertow's
  displayed inventory is now 24 self-reported tools; its older duplicate and
  inconsistent transport labels remain. Both entries stay `listed_incomplete`.

G2's Seiche and Undertow approvals remain pending verified public propagation.
SourceForge retains its separate owner, AWS remains paused, and the Claude
publisher flow still requires an account-owned review of the displayed terms.
None of those gates was bypassed by this work.

**StackShare:** the actual UI rejected the prepared form with **Bot access denied**.
No submission was accepted. The prepared form is retained for the account owner;
its ledger state remains `ready_account_action`.

**ToolHive:** the local candidate passed the official catalog validator and build.
Direct MCP discovery matched version 0.1.7 and the three router tools. The
unmodified ToolHive 0.51.4 CLI nevertheless requires an available container or
Kubernetes runtime before starting the remote proxy. No active local runtime was
available, so startup exited 1. A retained host-resource audit found elevated
memory pressure and nearly exhausted swap alongside an existing VM workload;
no additional runtime was started and no PR was submitted.
The candidate remains local only, with no public source URL and no new ledger
placement. Native proxy acceptance must pass before a contribution attestation.
These checks are synthetic/operator verification, not platform adoption.

Release versions, historical audit counts and prior full-ledger observation
clocks are preserved. Only the specified per-entry observations and this
expansion record are new.
