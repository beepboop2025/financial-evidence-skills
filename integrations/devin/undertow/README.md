# LiquiLens Undertow for Devin

Check what exiting a position at a given size may cost, and where liquidity has thinned, from public venue data with its timestamps and coverage.

This folder is the Devin package of the LiquiLens Undertow plugin, version
1.0.4. It connects to `https://api.seiche.info/undertow/mcp` without a product API key.
Devin may require its own account or plan.

Install it from a clone of this repository:

```sh
devin plugins install --local ./integrations/devin/undertow
```

Listing in the Devin marketplace is a separate review; none is claimed here.
The other client packages for this product are in
[`plugins/undertow`](https://github.com/beepboop2025/financial-evidence-skills/tree/main/plugins/undertow).
