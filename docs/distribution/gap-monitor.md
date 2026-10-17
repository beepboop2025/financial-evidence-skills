# Publication identity and channel gaps

The daily `Distribution publication gaps` workflow checks the exact public
identities in [channel-contracts.json](channel-contracts.json). It reports every
record from `marketplaces.json`, including submissions without listing URLs.
Unconfigured records say `not_monitored`; their declared ledger state is retained
separately. HTTP 200 never changes a ledger state or proves directory acceptance.

Run `python3 scripts/audit_distribution_gaps.py --output observation` for a
read-only public check, or add `--offline` for an inventory without network
requests. Pull requests run offline tests and the inventory. Scheduled and manual
runs retain JSON and a Markdown summary for 30 days, including failed checks.

The main package, GitHub release and MCP Registry expect
`docs/integrations.json:last_verified_release`. A newer candidate remains distinct
from that published baseline. NoiseFloor, LangChain, n8n, Activepieces, Wake and
the community service use their own ledger versions, never the root version.
The AI SDK reads its own package manifest and remains `pending_publication`
until `docs/distribution/ai-sdk-publication.json` explicitly has
schema `financial-evidence.ai-sdk-publication.v1` and `npm_published: true`, with
matching `package` and `version`, a source commit, an aware nonfuture observation
time and tarball hashes. After publication, the npm integrity must match that
receipt's `tarball_sha512_integrity`. Missing candidate
files or a pending receipt do not imply a zero result, a public package or users.

Each provider response must have the expected content type, schema and identity.
PyPI needs non-yanked distributions with SHA-256 metadata; npm needs integrity
metadata; MCP Registry needs the exact active/latest identity; GitHub needs a
published release with assets. The GitHub check confirms the exact recorded
release tag; it does not treat a repository's latest release (which may be a
different component) as the package's latest version. These checks observe registry metadata, not
artifact signatures, downloaded bytes or native installation. Re-run the
separate release/consumer acceptance procedure when publishing or changing an
artifact. The hosted context probes verify discovery links and metadata-only
authority boundaries; they do not open an SSE subscriber or measure market data.

Accepted GitHub directory entries are checked against their public default-branch
Markdown. Each check requires the named product link and its exact canonical URL,
outside HTML comments and fenced code examples. A removed or retargeted entry is
reported as drift even when the page returns HTTP 200. These checks confirm the
configured catalog rows, not native installation, referral traffic or adoption.
Glama repository listings and remote connectors have separate ledger records and
dated public observations. They are not silently treated as verified by a check
of an upstream package or endpoint. Glama's authenticated API and its quality
grades remain outside this credential-free scheduled monitor.

The process uses no credentials and does not follow redirects. Only reviewed
HTTPS hosts are permitted, with four workers, a 1 MB response limit and a
12-second subprocess deadline. Requests identify themselves as synthetic.
Receipts retain hashes and selected identity fields, never response bodies.

Exit 1 means a confirmed version/identity drift, missing resource, invalid
configuration or required channel missing from the ledger. Exit 2 means required
checks are unavailable or unverifiable, including rate limits, malformed
responses and provider failures. Exit 0 means configured checks passed, or an
explicitly labelled offline inventory. Neither outcome claims complete semantic
coverage of the ledger, universal agent adoption, trades or revenue. A timeout
does not mean a listing disappeared. Pending submissions need independent
maintainer/listing verification before a human updates their recorded state.

When adding a channel, declare its own expected-version source and exact public
identity, add a failure fixture, and preserve pending/owner/external gates. The
observer does not submit forms, publish packages, change deployments or send
messages to providers.
