# Security

The bundled fetcher is read-only. It accepts topic names, not arbitrary URLs,
and its source URLs are fixed in code. It requires HTTPS, rejects redirects,
limits response bytes, checks JSON content types and parses only JSON objects or
arrays. It sends no credentials and performs no financial transaction.

Report a suspected vulnerability privately through GitHub's security-advisory
interface for this repository. Do not include credentials or private financial
records in a public issue.
