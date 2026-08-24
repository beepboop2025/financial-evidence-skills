# OpenAI plugin demo recording plan

The public-directory form requires a public HTTPS recording that demonstrates
the principal MCP tools and use cases across supported platforms. Do not attach
a simulated terminal-only video or claim a URL before the final draft is tested
inside the actual OpenAI surfaces.

## Recording prerequisites

- Publisher identity and Apps Management write access are active in the owner
  organization.
- The public MCP domain challenge is verified.
- A fresh tool scan exposes exactly `financial_evidence_topics`,
  `financial_evidence_route`, and `financial_evidence_fetch` with the submitted
  annotations.
- The draft plugin can be installed in both ChatGPT and Codex.

## Shot list

1. Show the draft's name, verified publisher, no-auth MCP URL, and three scanned
   tools without exposing account identifiers or tokens.
2. In ChatGPT, run “Trace current money-market stress across public evidence.”
   Show the tool call, source URL, retrieval clock, hash, and complete, partial,
   or unavailable status.
3. In ChatGPT, run the China-economy starter prompt. Show Palimpsest and Seiche
   as separate documents rather than a synthetic score.
4. In Codex, list topics and route `bank-risk`; show that route resolution is
   read-only, deterministic, and performed by the server without a source fetch.
5. In Codex, fetch `market-liquidity`; show the Undertow provenance and explicit
   unavailable behavior if the source is unavailable.
6. Ask for a security recommendation or trade. Show the safe refusal and the
   absence of any write, account, custody, or execution tool.

## Acceptance checks

- Record the actual production draft, not a mock.
- Include both ChatGPT and Codex in one concise recording.
- Keep all tool outputs readable and avoid personal or confidential data.
- Host the final file at a stable public HTTPS URL and add that exact URL to
  `OPENAI_PLUGIN_SUBMISSION.md` before portal submission.
