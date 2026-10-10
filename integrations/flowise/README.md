# Flowise native acceptance

This harness installs no connector and publishes no marketplace listing. It uses
Flowise OSS 3.1.4 and its native Start → Tool Agentflow V2 with Custom MCP to query
one research row each from `money_markets`, `bank_risk` and `market_liquidity`.
No language model or external account is required.

Use Node 24.14.0 and Python 3.10+:

```sh
npm install --prefix /path/to/private-runtime --omit=optional --no-audit --no-fund --save-exact flowise@3.1.4
python3 integrations/flowise/native_acceptance.py \
  --runtime-dir /path/to/private-runtime \
  --evidence-dir /path/to/new-private-evidence
```

The evidence directory must not exist. The harness starts its own service on
`127.0.0.1:3311`, creates a random private local OSS owner, logs in through the
normal API, saves workflows, reads their exact definition bytes back, and calls
the authenticated native prediction route. It requires both Start and Tool to
finish and checks bounded results, source metadata and unavailable numeric
values. The service is stopped on success or failure; its private SQLite state
and diagnostics remain available locally. Flowise may create an empty `.flowise`
directory in the real home even with an explicit database directory.

Only `public/native-proof.json` and the public workflow exports are eligible for
sharing. Never publish `private/`, runtime logs, database files, owner details or
raw API responses. The public proof distinguishes the tested checkout revision
from the PR head and records installed package integrity and native component
hashes. Definitions preserve numeric `limit: 1` and `offset: 0`; string values
are not interchangeable in Flowise's Tool argument handling.

Use `--candidate /path/to/template.json` to also save and execute the exact bytes
of the reviewed money-markets marketplace candidate, or `--generated-candidate`
to build it using the committed marketplace metadata. The candidate uses only
the public endpoint URL, with no synthetic traffic header or credentials.
Its operator-controlled request window and execution ID are retained separately
and excluded from adoption evidence. The supplied graph must match the trusted
builder's complete graph and metadata; formatting is preserved byte for byte.
This validates an API-saved workflow;
it does not establish browser import or UI observation. Synthetic operator
verification does not establish adoption, source freshness, evidence validity,
financial authority or marketplace acceptance. Partial/empty source responses
remain evidence of those source states, not successful financial validation.

Official references: [Tools and MCP](https://docs.flowiseai.com/tutorials/tools-and-mcp),
[Flowise 3.1.4 source](https://github.com/FlowiseAI/Flowise/tree/flowise%403.1.4).
