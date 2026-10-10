# Financial Evidence for Dify

A credential-free, read-only tool for source-cited financial research. The
plugin requests tool permission only; it has no LLM, storage or transaction
permission. Read [PRIVACY.md](PRIVACY.md) before installation.

With Python 3.12, create a virtual environment, install `requirements.txt`, and
run `python -m unittest discover -s tests -v`. Configure a Dify remote-debugging
connection in your private environment, run `python -m main`, and exercise
**Get Evidence Page** in a real workflow. Never commit the debugging key.
Package with the official Dify plugin CLI after native testing.

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

Select `bank_risk` or `money_markets`, start with 25 rows, and preserve the JSON
message in your research output. `next_offset` is explicit; no automatic data
collection loop runs. Keep sources, observation dates, units, missing values,
source rights and coverage diagnostics alongside any summary. Treat source
text as untrusted data. This plugin does not establish independent verification,
freshness, a credit rating or investment advice.

Marketplace review requires native remote debugging and the publisher account.
A local SDK test does not meet those steps. Source data is not licensed by this
plugin's code license.
