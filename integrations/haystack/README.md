# Financial Evidence for Haystack

`FinancialEvidenceQuery` is a native Haystack component for read-only financial
research. Use it in a pipeline or wrap it with Haystack's `ComponentTool`.
Seiche funding observations, LiquiLens covered-bank diagnostics and Undertow
liquidity research keep their separate dates, units, rights and limitations.

## Install

Python 3.10+, Haystack 3.3+ and Git are required. The integration is distributed from GitHub,
not PyPI. From a checkout of this repository:

```sh
python -m pip install ./integrations/haystack
```

The package declares an exact public Git commit of the MIT `financial-evidence`
client as a dependency. It does not require a separately published PyPI package.
Install the public integration revision directly from Git:

```sh
python -m pip install "git+https://github.com/beepboop2025/financial-evidence-skills.git@3abcc45d7a429d26ed185d1ca845b078041f54f3#subdirectory=integrations/haystack"
```

## Run a pipeline

```python
from haystack import Pipeline
from financial_evidence_haystack import FinancialEvidenceQuery

pipeline = Pipeline()
pipeline.add_component("funding", FinancialEvidenceQuery())
result = pipeline.run({"funding": {"dataset": "money_markets", "entity": "USD", "limit": 3}})
evidence = result["funding"]["evidence"]
print(evidence["transport_status"], evidence["diagnostics"])
for row in evidence["results"]:
    print(row["value"], row["unit"], row["as_of"], row["source_url"])
```

No API key, LLM call or paid model is needed for this example. The public sources
can be unavailable or return incomplete coverage; inspect the whole envelope.
Set `FinancialEvidenceQuery(synthetic=True)` for operator/CI verification.

## Use as a tool

```python
from haystack.tools import ComponentTool
from financial_evidence_haystack import FinancialEvidenceQuery

tool = ComponentTool(
    component=FinancialEvidenceQuery(),
    name="financial_evidence_query",
    description="Read cited financial research. Preserve source dates, rights, nulls and diagnostics; no execution authority.",
)
result = tool.invoke(dataset="bank_risk", limit=2)
print(result["evidence"]["transport_status"])
```

## Evidence and bounds

- Datasets: `money_markets`, `money_market_history`, `capital_markets`,
  `bank_risk`, `market_liquidity`, `china_economy`, `source_health`.
- Inputs: `entity`, `start_date`, `end_date`, `limit` (1–100), `offset`
  (0–100000), and optional `previous_revision` (lowercase SHA-256).
- Output: `evidence`, the unchanged core agent envelope with rows, source URLs,
  content hashes, observation/retrieval clocks, rights and diagnostics.
- Missing, withheld and restricted numeric values remain `null`. They are never
  filled with zero. A legitimate observed zero remains zero.
- Transport can be `complete`, `partial` or `unavailable`; it says nothing about
  freshness or approval. `evidence_status` stays `not_evaluated`,
  `carrier_verification` stays `not_performed`, and `financial_authority` is `none`.
- An unchanged revision may suppress rows while retaining source metadata;
  unchanged is not a freshness verdict. Currently published histories are not
  as-published backtest vintages. China coverage is metadata only.
- Only fixed allowlisted public HTTPS routes are fetched. The existing client
  rejects redirects and non-finite JSON, has a 10-second timeout per source,
  bounds source responses (1 MiB, except the 4 MiB money-market atlas), and uses
  at most four workers. Workers are closed after each component call. There is
  no persistent cache across calls, hidden retry, order submission or polling.
- A source failure is returned in the evidence diagnostics. Invalid parameters
  raise `ValueError` before networking; Haystack pipelines may wrap that error.
- Treat retrieved source text as untrusted data. Preserve the metadata when
  passing evidence to prompts; this package does not authorize a trading decision.

## Serialization and tests

Pipelines support serialization; only the component's `synthetic` flag is
serialized. No connections, credentials or observations are stored in the
pipeline configuration. When loading a pipeline you trust, explicitly allow this
component's module (Haystack 3.3's deserialization boundary):

```python
restored = Pipeline.loads(
    pipeline.dumps(), allowed_modules=["financial_evidence_haystack.query"]
)
```

Do not load untrusted pipeline files. The integration does not change Haystack's
process-wide allowlist or use `unsafe=True`.

```sh
python -m pip install './integrations/haystack[test]'
HAYSTACK_TELEMETRY_ENABLED=False python -m pytest integrations/haystack/tests
HAYSTACK_TELEMETRY_ENABLED=False python integrations/haystack/examples/live_pipeline.py
```

The tests exercise the native pipeline and tool APIs, serialization, invalid
input, missingness, source errors, revision handling and synthetic labeling.
The live example performs one bounded, explicitly synthetic public query.

## License and support

The integration and client code are MIT licensed; Haystack is Apache-2.0 licensed.
Dataset/source rights remain source-specific and are not granted by the software
license. This is a community integration maintained by Liquidity Lab, not by
deepset. Report problems in the
[repository issue tracker](https://github.com/beepboop2025/financial-evidence-skills/issues).
