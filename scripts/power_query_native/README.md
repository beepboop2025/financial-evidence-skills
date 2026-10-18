# Native Power Query acceptance

The Windows workflow downloads Microsoft's `Microsoft.PowerQuery.SdkTools`
NuGet package **2.155.2**, verifies its pinned SHA-512 from NuGet's versioned
catalog, and runs the actual `PQTest.exe` engine. No local Windows installation,
customer account, credential or production data is needed.

`generate.py` embeds the exact shipped three `docs/office/*.pq` expressions in
an M query. Only `Web.Contents` is replaced lexically with deterministic fixture
responses. The real engine executes the shipped contract checks, transformations,
rights suppression and output tables. Source SHA-256 hashes appear in the
retained receipt.

Twenty-two assertion groups cover positive, zero, negative and missing numbers;
restricted values; literal formula-like text; source dates and gaps; exact
watchlist coverage; selection limits; and rejection of malformed identities,
partial transport, pagination, row counts and unexpected financial authority.
A separate query with an intentionally wrong zero-value assertion must fail.
The runner checks engine statuses and evaluated output, not merely process exit
or source text. Raw engine output and generated test queries are retained.

This establishes **Power Query engine execution with synthetic fixtures**.
It does not establish native Excel UI refresh, live HTTP connectivity, a
marketplace approval, or independent adoption.

```powershell
python scripts/power_query_native/accept.py C:\approved-sdk\tools\PQTest.exe .\power-query-native
```

References: [Microsoft commands/options](https://learn.microsoft.com/en-us/power-query/sdk-tools/pqtest-commands-options),
[general usage](https://learn.microsoft.com/en-us/power-query/sdk-tools/pqtest-general-usage),
[pinned NuGet catalog](https://api.nuget.org/v3/catalog0/data/2026.06.03.23.57.02/microsoft.powerquery.sdktools.2.155.2.json).
