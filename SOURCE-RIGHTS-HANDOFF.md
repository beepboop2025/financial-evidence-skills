Native input rights change, 6 November 2026

Base: origin/main a0ddf0c (0.1.17 documentation lineage). This change is local source only. Published package 0.1.17 and Worker 0.1.16 were the last independently verified release states in the fleet closeout; neither was changed here.

ProductClient now applies a targeted deny gate before returning or caching native MCP results. It covers attributed Coinbase, FRED, Binance Vision, OONI, Telegram, unofficial Yahoo, and free hosted Open-Meteo inputs. Both JSON text and structured MCP representations are inspected. A tainted mixed result is replaced in full so sibling totals, prose, and embedded resources cannot retain dependent data. Original-response and returned-payload hashes remain distinct. No paid API, upstream market-data fetch, mail, archive deletion, or licence grant occurs.

This does not claim positive qualification of every other source. The existing source-access catalog remains a pilot qualification registry; this gate cannot convert it into an exact-observation entitlement. Historical download-time grants remain valid in their original scope; actual archived data needs a reviewed grant binding before adapter admission. Unknown sources are still marked as requiring source qualification.

Tests: native rights regressions plus publication_rights, product_learning and trading_transport. Use PYTHONPATH=src python3 -m pytest with temporary files on FastWorkspace. Some transport tests require optional runtime dependencies and are skipped when absent. Deployment/publishing is reserved for the root release coordinator and existing release workflows.
