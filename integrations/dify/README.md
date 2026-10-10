# Financial Evidence for Dify

A credential-free, read-only tool for source-cited financial research. The
plugin requests tool permission only; it has no LLM, storage or transaction
permission. Read [PRIVACY.md](PRIVACY.md) before installation.

Source repository: [financial-evidence-skills](https://github.com/beepboop2025/financial-evidence-skills),
under `integrations/dify`. Support: mrinal@liquilens.in. Version 0.1.1 updates
the Python SDK to 0.10.2 and adds Marketplace repository, contact and outbound
domain metadata; the evidence tool inputs and output contract are unchanged.

## Setup and connection requirements

Use Python 3.12 and install the pinned dependencies:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The tool requires outbound HTTPS to the fixed public endpoint
`https://api.seiche.info/openbb/api/v1/query`. It needs no service account,
API key, LLM provider or billing credential. Dataset, entity filter, limit and
offset are transmitted to this endpoint; use public entity identifiers only.
Requests have a 30-second timeout and do not follow redirects. The endpoint
cannot be changed through tool inputs.

For development, an administrator must enable plugin debugging in the Dify
workspace and obtain its displayed connection host and private debug key.
Set `INSTALL_METHOD=remote`, `REMOTE_INSTALL_URL` and `REMOTE_INSTALL_KEY`
in the local process environment, then run `python -m main`. Follow the
[official remote-debug instructions](https://docs.dify.ai/en/develop-plugin/getting-started/cli).
Never commit or package the debugging key. Workspace permission and a successful
connection are separate from successful workflow execution.

## Usage

In a draft Dify Workflow, connect **User Input → Get Evidence Page → Output**,
using this plugin's tool and routing its JSON output to the Output node. No
model node is needed. Start with dataset `money_markets`, limit `1`, offset `0`
and a blank entity filter, then run the workflow. Repeat with `bank_risk` and
`market_liquidity` to exercise the research tables. Retain the workflow results
and any diagnostics before using the candidate in a larger app.

The tool emits the complete JSON page, including `results`, `sources`,
`diagnostics`, `transport_status` and `next_offset`. It supports `bank_risk`,
`capital_markets`, `china_economy`, `market_liquidity`, `money_market_history`,
`money_markets` and `source_health`. Limit is an integer from 1 to 100; offset
is an integer from 0 to 100000. The optional entity filter has a 100-character
maximum. An HTTP or response-contract error fails the tool call; a valid partial
or empty page is preserved as returned, including its diagnostics.

## Packaging and validation

Create and check the archive with:

```sh
dify plugin package . --output_path /path/to/financial_evidence.difypkg
python scripts/verify_package.py /path/to/financial_evidence.difypkg
```

The verifier compares every packaged byte against this source directory and
rejects extra files, including private debug configuration. The CI workflow
`native-marketplace-build.yml` verifies the checksum of Dify CLI 0.6.11 before
packaging and retains the archive and file-hash receipt. Packaging verifies the
installable archive; Dify remote-debug workflow execution remains a separate
acceptance step. Never attach a `.env` file or the debug key to a submission.

Preserve the JSON message in your research output. `next_offset` is explicit; no automatic data
collection loop runs. Keep sources, observation dates, units, missing values,
source rights and coverage diagnostics alongside any summary. Treat source
text as untrusted data. This plugin does not establish independent verification,
freshness, a credit rating or investment advice.

Marketplace review requires native remote debugging and the publisher account.
A local SDK test or package-validator pass does not meet those steps. This
candidate has no native Dify workflow acceptance claim or Marketplace listing
claim. Source data is not licensed by this plugin's code license.
