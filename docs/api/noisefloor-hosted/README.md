# Hosted NoiseFloor client kit

Use the central service at `https://agents.seiche.info/v1/noisefloor`. Import the Postman or Bruno collection,
use the OpenAPI schema, or run the standard-library Python client:

```sh
python hosted_review.py spectral seiche.json --synthetic --output review.json
python hosted_review.py dyson dyson.json --synthetic --output reference.json
```

The six sample panels and Dyson request are synthetic examples. For your own
permitted input, select one JSON request and omit `--synthetic`. The client
sends that selected JSON to our server; no data is fetched from your files
unless you supply its path. The server counts operation demand and outcomes;
private request bodies and arbitrary text are not stored in demand metrics.
Inspect the [current privacy notice](https://agents.seiche.info/privacy).

An unavailable service remains an error. This client has no local assessment
or native-origin fallback. Outputs preserve source clocks, gaps and research
limits. No operation authorizes a trade or establishes predictive performance.

The [0.4.0 archive](../noisefloor/) retains its original bytes and offline
implementation. This hosted kit derives its input schemas and synthetic panels
from that verified source; it is not a new NoiseFloor algorithm release.
MCP: https://agents.seiche.info/products/noisefloor/mcp
