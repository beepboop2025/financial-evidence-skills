# Use the same check in your agent or scheduler

Run a [funding watch, institution watch or BTC exit check](workflows.html), then
bring the same selection into your own workflow. The Python starter requires
Python 3.10 or later, with no packages, model account or data API key.

Download and inspect [research_watch.py](research_watch.py), then run:

```sh
python3 research_watch.py --workflow funding --selection USD --output captures
python3 research_watch.py --workflow institutions --selection au-sfb,bajaj-finance --output captures
python3 research_watch.py --workflow exit --selection 10000,100000 --output captures
```

Each command prints its capture directory. Inside are the original `result.json`
and a `receipt.json` binding the saved bytes with SHA-256. Each run creates a new
directory; earlier captures remain intact. The institution slugs and sizes are
illustrative. Select your own supported research inputs.

The script makes one bounded public request per run, refuses redirects and
checks the response selection, original product schema and evidence digest.
Exit code `0` means a prepared research response, `2` means no prepared evidence,
and `1` means a request, validation or local-write failure. None establishes
freshness or financial suitability. A receipt detects changed files; it is not
an independent source attestation.

## Compare the next review

Use a prior capture, or the full JSON downloaded from the browser, for the same
workflow and selection:

```sh
python3 research_watch.py --workflow funding --selection USD \
  --previous captures/YOUR_PREVIOUS_CAPTURE/result.json --output captures
```

The new directory also contains `comparison.json`, with before/after evidence
fields. Retrieval times alone do not count as a change. Source dates, values,
units, availability and rights still need review. Institution fingerprints can
change because of aging or policy as well as underlying evidence. Open the
institution's full record before interpreting the difference.

Funding responses with `next_offset` need the [paginated research kit](../tools/)
for a complete table. Exit checks retain the original published rungs and
withheld values; the script never interpolates an unsupported size.

## Add it to an existing agent

Place the downloaded file beside your agent code:

```python
from research_watch import fetch_workflow

funding = fetch_workflow("funding", "USD")
watchlist = fetch_workflow("institutions", "au-sfb,bajaj-finance")
exit_check = fetch_workflow("exit", "10000,100000")
# Pass the original evidence, source dates and limitations to your research step.
print(funding["evidence"])
```

These ordinary Python functions work in an existing research process. For native
LangChain/LangGraph, CrewAI, OpenAI Agents or Pydantic AI tool registration, use
the [framework adapters](https://github.com/beepboop2025/financial-evidence-skills/tree/agent-v1.0.0/integrations/agents).
For an MCP client, use the [connection guide](../agents/CONNECT.md). The public
[API client kit](../api/) includes all three workflows in Postman, Bruno,
Insomnia/OpenAPI and HTTP-client formats.

## Repeat when your task needs it

After the manual run works, add that exact command to your existing scheduler
using absolute paths for Python, the script and a private capture directory.
Choose a cadence that matches the source: quarterly disclosures do not become
intraday observations through frequent polling. The script runs once and exits;
downloading it does not install a schedule or send alerts. For managed local
research jobs, see the [recurring runtime](../agents/runtime.html).

Keep captures under your own access and retention policy. Source data rights
remain separate from this script's MIT code license. Do not publish captured
data merely because the script is public. The starter does not enroll a
measurement identity. Operator acceptance runs should add `--verification` so
their requests are marked synthetic and are not treated as customer evidence.

For economic context beyond these three tasks, use the
[Palimpsest dataset](./?dataset=china_economy) and
[NoiseFloor's caller-supplied analysis](../agents/CONNECT.md#optional-market-and-headline-analysis).
Each product keeps its own coverage and authority.
