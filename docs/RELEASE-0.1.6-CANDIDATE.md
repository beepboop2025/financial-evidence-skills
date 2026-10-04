# Financial Evidence 0.1.6 candidate

This source adds `gift-city`, `forex` and `gold` to the existing five topics.
It is not a package, Registry or hosted MCP release. Published installation
links and `last_verified_release` stay at 0.1.5 until independent publication
proof is accepted. The immutable `financial-evidence-mcp-v0.1.5.json` contract
and historical release evidence are retained unchanged.

## Included behavior

- CLI, stdio MCP, the standalone helper, its Gemini mirror and shared packet
  service accept all eight topics. Existing topic names retain their behavior.
- GIFT City and gold read `https://api.seiche.info/api/v2/gift-city` once per
  packet, preserving separate requested-topic records with one source receipt.
- Forex reads `https://api.seiche.info/api/v2/world-markets?section=forex`.
  Quote selection remains a separate native Seiche `market_workbench` request.
- Explicit adapters retain source-reported response/section states and source
  clocks. Partial/gated context, null gold prices and per-row missingness remain
  in the source document. Retrieval success is not evidence evaluation.
- Skill guidance serves gold/treasury desks, investors/fund managers and
  banks/IFSC institutions. It routes requested gold calculations to native
  Seiche and Undertow tools only after the user supplies the necessary inputs.
  The helper cannot fetch arbitrary URLs or execute a scenario.

The seven existing OpenBB tabular datasets, historical workflow examples and
separately versioned Workspace release are not expanded into new table schemas
by this patch. The published workflow example intentionally requires 0.1.5
until separately reviewed. Current source route/fetch surfaces carry the new
topics; a downloaded skill does not upgrade a remote MCP endpoint.

## Normal release requirements

1. Review the exact source and normal pull-request checks. Retain clean source
   identity, unchanged historical artifacts, eight-topic contract parity,
   fixed-URL/redirect/size/error tests and the source-clock boundaries.
2. Coordinate the LiquiLens site remote router update independently. Its
   `initialize` and `tools/list` must match
   `integrations/financial-evidence-mcp-v0.1.6.json`, including server version,
   canonical tool hash, eight-topic enum, bounds and read-only annotations.
   Retain exact Worker source/deployment identity and useful bounded fetch proof.
3. Use the existing signed-release lane. The `release-container.yml` preflight
   verifies the release tag, signed commit, exact main, all version manifests,
   Python/JavaScript suites, and the exact live Worker/versioned MCP contract.
   The updated verifier requires 0.1.6; an unchanged 0.1.5 remote must block it.
4. The existing release jobs produce the multi-architecture OCI image, Registry
   record and downloadable package/bundle artifacts with integrity evidence.
   Do not create a tag or advertise those artifacts before the coordinated
   gate is satisfied. Homebrew and other downstream installation pins remain
   distinct distribution work.
5. Update published discovery metadata only after readback verifies actual
   release artifacts and remote behavior. Refresh product skill URLs and hashes
   to one reviewed immutable source commit; mutable branch URLs cannot replace
   immutable receipts.

The standalone skill and helper can be reviewed/downloaded from an exact source
commit before package release. That source availability is not proof of a
published 0.1.6 wheel, container, vendor listing, installed agent usage or paid
adoption. The prior source, signing pins and release checks must not be bypassed.
