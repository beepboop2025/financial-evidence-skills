# Native office acceptance

This page records completed native checks and their limits. A working import,
query, marketplace listing and independent analyst adoption are different results.

## Microsoft Power Query engine — passed

On 18 October 2026, the [Windows acceptance workflow](https://github.com/beepboop2025/financial-evidence-skills/actions/runs/39114203632)
passed against source commit `b6266ce063d2b1c37ff4a47fb710ab8f72b3b495`.

| Component | Verified version or scope |
| --- | --- |
| Runtime platform | GitHub-hosted `windows-2022` runner |
| Microsoft SDK package | `Microsoft.PowerQuery.SdkTools` 2.155.2, pinned SHA-512 checked before extraction |
| PQTest application | 2.155.2.0 |
| Microsoft Mashup Engine | 2.155.504.0 |
| Shipped expressions | `FinancialEvidenceRows.pq`, `FinancialEvidenceFunding.pq`, `FinancialEvidenceWatchlist.pq` |
| Results | 22 assertion groups passed; separate deliberately incorrect numeric assertion rejected |
| Transport | Only `Web.Contents` replaced with deterministic synthetic fixture responses |

The harness embeds the actual shipped query expressions unchanged. Microsoft's
engine executes their data validation and table transformations. The successful
result is checked in the engine's evaluated output, and the failing control must
produce the precise expected error. A process exit code of zero alone is
insufficient: the engine can use it when a query test fails.

The checks cover:

- Positive, zero, negative and null numeric values, literal formula-like source
  text, source URLs and original observation/retrieval dates.
- Funding currency normalization, deduplication and bounds; distinct zero/missing
  states; restricted values withheld while their restriction remains visible.
- Exact institution coverage, explicit uncovered selections, zero versus missing
  metrics, source gaps, warnings and evidence limits.
- Rejection of malformed schemas, wrong dataset/selection identity, incomplete
  transport, unresolved pagination, incorrect row counts, duplicate/omitted
  institutions and unexpected financial authority.

The artifact named `power-query-native` contains the generated queries, engine
outputs, version record and acceptance receipt. Both actual Windows checkout
hashes and LF-normalized source hashes are retained. The latter match the
published query source:

```text
9009772b17e128897068a1acea895563cd15f7ae18381fa5253d54adbde9e9f0  FinancialEvidenceRows.pq
08df13f125330f2d54e41d01f4bbfa5e73e084f5c7a3de0b94d4e071efb257f3  FinancialEvidenceFunding.pq
0f568da06fdd04ac424d0fd5832aba222b8f04c43bf23998d0136910ae756a2b  FinancialEvidenceWatchlist.pq
```

This verifies **Microsoft Power Query runtime behavior with controlled HTTP
fixtures**. It does not establish Excel UI refresh, live network authentication,
an add-in marketplace approval or independent usage. Native Excel UI and live
service checks require their own evidence.

The [test harness](https://github.com/beepboop2025/financial-evidence-skills/tree/main/scripts/power_query_native)
and [workflow](https://github.com/beepboop2025/financial-evidence-skills/blob/main/.github/workflows/power-query-native.yml)
make the check repeatable. Microsoft's [PQTest commands](https://learn.microsoft.com/en-us/power-query/sdk-tools/pqtest-commands-options)
describe the engine interface used here.
