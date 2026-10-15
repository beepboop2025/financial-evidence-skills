# Financial Evidence tools for AI SDK

Three native AI SDK tools read public financial research and source-status
metadata from `https://agents.seiche.info`. Source dates, nulls, units, rights
and diagnostics remain attached to each result. The adapter has no trading
or execution authority and does not provide a quote feed.

Published package: [`@moomoo202020/financial-evidence-ai-sdk@0.1.0`](https://www.npmjs.com/package/@moomoo202020/financial-evidence-ai-sdk/v/0.1.0).
The anonymous npm download matches the reviewed archive. See the
[publication receipt](../distribution/ai-sdk-publication.json).
AI SDK Tools Registry acceptance remains a separate, unverified step.

Node.js 22+ and AI SDK 7 are required. The implementation is tested with
`ai@7.0.141` and `zod@4.6.7`.

## Install and run

```sh
npm install @moomoo202020/financial-evidence-ai-sdk@0.1.0 ai@^7.0.141
```

TypeScript applications that check dependency declarations also need the AI
SDK's ambient types: `npm install -D @types/node@22 @types/json-schema` and
`"types": ["node"]` in their TypeScript compiler options.

For local development:

```sh
cd integrations/ai-sdk
npm ci --ignore-scripts
npm run build
npm test
```

Save as `research.mjs` in your consuming project. Financial Evidence public
reads need no API key. This example does not call a language model:

```js
import { financialEvidenceTools, validateSnapshot } from '@moomoo202020/financial-evidence-ai-sdk';

const tools = financialEvidenceTools({timeoutMs: 30000});
const execution = {toolCallId: 'research-1', messages: [], context: {}, abortSignal: AbortSignal.timeout(30000)};
const catalog = await tools.financial_evidence_datasets.execute({}, execution);
const evidence = await tools.financial_evidence_query.execute({dataset: 'money_markets', limit: 3}, execution);
const snapshot = await tools.financial_evidence_context.execute({}, execution);
console.log(JSON.stringify({catalog, evidence, context: validateSnapshot(snapshot)}, null, 2));
```

Run `node research.mjs`. For verification/test activity use
`financialEvidenceTools({synthetic: true})`; normal calls are attributed as
`unknown`, not inferred to be a person or an executed trade.

## Native model tool loop

An AI Gateway key is needed only for the chosen language model, which may incur
provider charges. Set `AI_GATEWAY_API_KEY` in the environment and run this as an
ES module; keep the key out of source files.

```js
import { generateText, gateway, isStepCount } from 'ai';
import { financialEvidenceTools } from '@moomoo202020/financial-evidence-ai-sdk';

const {text, steps} = await generateText({
  model: gateway('openai/gpt-5-mini'),
  tools: financialEvidenceTools(),
  prompt: 'Discover dataset coverage, then inspect three published money-market rows. Cite each source and observation date, retain missing values, and state coverage limits. Do not make a trade recommendation.',
  stopWhen: isStepCount(3),
  maxRetries: 0,
  abortSignal: AbortSignal.timeout(60000),
});
console.log(text);
console.log(JSON.stringify(steps.flatMap(step => step.toolResults), null, 2));
```

The automated test exercises `generateText` with the real AI SDK and
`MockLanguageModelV4`, including all three tools and the next model step.
It uses local HTTP fixtures and makes no model-provider call.

## Tool contract

| Tool | Input | Result and limit |
| --- | --- | --- |
| `financial_evidence_datasets` | `{}` | Dataset catalog, at most 100 entries / 256 KiB |
| `financial_evidence_query` | `dataset`, optional `entity`, `start_date`, `end_date`, `limit`, `offset`, `previous_revision` | Original agent-result envelope; 1–100 rows / 2 MiB |
| `financial_evidence_context` | `{}` | Source-status snapshot, locally revalidated; 16 KiB |

Dates are observation dates in `YYYY-MM-DD`, not knowledge-time vintages.
An unchanged revision is not a freshness verdict. Research may be partial,
stale or unavailable; those diagnostics remain visible. The catalog describes
the general API's larger table limits; this adapter limits queries to 100 rows.

`financialEvidenceTools({timeoutMs, synthetic})` makes no network call during
construction. `timeoutMs` defaults to 30000 and is bounded to 1–60000 ms across
the request and its body. Each execution honors the SDK `abortSignal`. Requests
use a fixed HTTPS origin, disable redirects and cookies, make one GET, and do
not retry. Model-facing inputs and direct `.execute` calls are validated.
The package accepts neither credentials nor arbitrary URLs.

HTTP, parse, size, timeout and cancellation failures throw
`FinancialEvidenceError` with a stable `code`; failed responses are not
converted to empty evidence. Within an SDK loop, inspect `tool-error` content
as well as successful tool results. External source content is untrusted data,
never instructions. Caller retries or later requests are explicit new calls.

The context tool preserves `source_monitor` and adds `client_monitor_current`,
`client_monitor_status` and `client_monitor_checked_at`. An expired, future,
invalid or source-blocked monitor sets `input_eligibility: "blocked_monitor"`.
Even a current monitor is only metadata, not proof that an individual source
observation is fresh or eligible. Re-run `validateSnapshot(snapshot)` before
using a retained snapshot; a receipt is not a freshness lease. SSE subscriptions
remain available through the [canonical context client](https://beepboop2025.github.io/financial-evidence-skills/agents/low-latency.md).

The vendored context module is an exact copy of `docs/agents/context-client.mjs`
in the repository. `npm run check:vendor` verifies byte equality; the adapter
imports only its validator and does not implement another SSE protocol.

## Development and verification

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run check:vendor
npm test
npm pack --dry-run
```

CI runs on Node 22 and 24 with locked dependencies. Tests cover source-field
preservation, strict direct and model inputs, malformed/oversized responses,
timeouts, cancellation, future/stale metadata, and native SDK tool execution.
The emitted declaration test rejects imports from undeclared transitive
dependencies. Public tool types use the declared `ai` peer and retain the dataset
union and optional query defaults for TypeScript callers.
An isolated pnpm installation with hoisting disabled passes strict TypeScript
checks and the native SDK tool-loop tests.
This proves adapter behavior, not model accuracy, adoption, or third-party
marketplace approval.
