# Haystack integration

The separately installable [`financial-evidence-haystack`](../integrations/haystack)
package exposes `FinancialEvidenceQuery`, a native Haystack pipeline component
that can also be wrapped in `ComponentTool`. Its complete usage, input/output
contract, installation and validation commands are in the
[package README](../integrations/haystack/README.md).

The package reuses the MIT financial-evidence client pinned to an exact public
Git commit. It does not depend on a nonexistent PyPI release. It preserves each
product's evidence metadata and complete/partial/unavailable transport state.

Haystack's public catalog requires an installable, runnable package, a repository
and issue link, examples and licensing details. A catalog submission is a request
for maintainer review; this package's existence does not mean the upstream
catalog has accepted it or that external users have adopted it.

- [Haystack integration requirements](https://docs.haystack.deepset.ai/docs/integrations)
- [Official catalog contribution template](https://github.com/deepset-ai/haystack-integrations/blob/main/draft-integration.md)

Current source pins the hosted Financial Evidence client at immutable revision
`65cfb5437f3c3aad9f6270808d00e3392b12b42e`. Upgrade the integration to use the central service;
older installed dependency pins retain their original behavior.
