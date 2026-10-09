# NoiseFloor 0.4.0 research client kit

Import `noisefloor.postman_collection.json` into Postman, open this folder in
Bruno, import `openapi.json` into an OpenAPI client, or run `noisefloor.http`.
The two default requests are explicitly synthetic. The six product JSON files
are alternative panels for the spectral endpoint, not current product data.

```
curl -H 'Content-Type: application/json' --data-binary @seiche.json https://api.seiche.info/noisefloor/v1/spectral/assess
curl -H 'Content-Type: application/json' --data-binary @dyson.json https://api.seiche.info/noisefloor/v1/research/dyson
```

Use permitted, non-confidential data on the public endpoint. For private data,
install `noisefloor==0.4.0` and run locally. `spectral_review.py` adapts a complete
retained Financial Evidence table: run `python spectral_review.py --help`.

Keep rights, source dates, knowledge clocks and missingness. Select comparable
metrics; short current snapshots cannot provide a correlation history. The
Marchenko-Pastur band is an asymptotic reference, not a significance test. Dyson
paths are synthetic, not market-calibrated. No tool has execution authority.

MCP: https://api.seiche.info/noisefloor/mcp
Workbench: https://liquilens.in/agents/correlation/
Methods: https://github.com/beepboop2025/noisefloor/blob/v0.4.0/docs/SPECTRAL_RISK.md
