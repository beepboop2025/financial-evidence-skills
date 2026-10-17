# One task, one saved review

These commands are a **source-checkout preview**, not part of the published
0.1.10 wheel. From this checkout, install the base package in your own environment:

```sh
python3 -m pip install .
financial-evidence start
financial-evidence review funding --output reviews
```

Python 3.10+ is sufficient. No optional dependencies, model or data API key are
needed for this path. `start` is entirely offline: it shows the same authored
task, browser link, API route and MCP arguments used by the hosted onboarding
catalog. `review` performs one bounded read of that task from the central service.
It does not schedule polling, register a user or send messages.

The terminal shows a short source-cited table. The printed capture directory
contains the original `result.json`, a readable `brief.md` and a `receipt.json`
that binds their bytes. Existing captures are preserved. Share a brief only after
checking its original sources, dates, gaps and source-specific permitted use.
The brief shows at most 25 rows; the complete returned evidence remains in JSON.

## Return to the same task

At the next useful review time, supply the previous capture's actual path:

```sh
financial-evidence review funding --output reviews \
  --previous reviews/YOUR-PREVIOUS-CAPTURE/result.json
```

This also saves `comparison.json`. The comparison excludes retrieval clocks and
retains observation dates, missing evidence and the workflow's review fields.
Institution fingerprints include review aging and policy changes. A changed
response does not by itself establish a new financial event; an unchanged one
does not establish freshness. An incomplete baseline is not silently replaced.

Choose another supported task with explicit scope:

```sh
financial-evidence start institutions
financial-evidence review institutions --selection au-sfb --output reviews
financial-evidence review exit --selection 10000 --output reviews
```

Funding is system context, institution reviews cover published disclosures, and
BTC estimates are indicative research. None supplies an executable order, credit
approval or guarantee. Unsupported selections remain visible as gaps.

## Use the same client in Python

```python
from financial_evidence.research import fetch_workflow, save_review

result = fetch_workflow("funding", "USD")
directory = save_review(result, "reviews")
print(result["prepared_response"], directory / "brief.md")
```

`fetch_workflow` rejects a mismatched selection, unexpected source schema,
modified evidence digest, non-finite JSON, redirects and oversized responses.
`save_review` can take a validated previous capture via `previous=...`.
The standalone [research_watch.py](../start/research_watch.py) is generated from
the same module and remains usable without installing a package.

## Automation and verification

Use `--format json` for machine-readable output. With `--output`, JSON stdout
contains the capture path; without it, stdout contains the full response. With
Markdown, the brief goes to stdout and the capture path goes to stderr.

`review` exit codes: **0** = the service prepared evidence; **2** = a response was
retained but no prepared result was available; **1** = retrieval, validation or
storage failed. CLI argument parsing errors also use argparse's exit code 2.
These meanings are specific to `review`; existing `fetch` codes still describe
transport only. Prepared evidence is not a completed human task or a freshness
verdict.

Use `--verification` (or `verification=True` in Python) for operator/CI calls so
they are labelled synthetic. No installation identifier or analytics enrollment
is created. Public service operational measurement still applies. Record useful
task completion and returning pilot teams through the existing consented
evaluation process; downloads and test traffic cannot establish retention.

Developers: after changing `src/financial_evidence/research.py`, run
`python3 scripts/build_research_watch.py`. The mirror check and client tests
protect both installation paths.
