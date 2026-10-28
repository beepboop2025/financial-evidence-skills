# OpenAI review packages

The Financial Evidence OpenAI ZIP is independently versioned at 0.1.17. Its source manifest is `financial-evidence/plugin.json`; the Python, container, Claude and root Codex release remain 0.1.16. This candidate changes listing text and review metadata only, retaining the same seven runtime assets and MCP connection.

Run `python3 scripts/build_openai_submission.py` to regenerate the ZIP and content receipt, or add `--check` to verify committed bytes. Review cases describe expected behavior; they are not model-run results or directory approval. The walkthrough video has not been recorded, so no demo URL is declared.

The manifest follows https://developers.openai.com/plugins/deploy/submission. Review cases must contain exactly five positive and three negative cases. Positive tool names must be checked against the hosted server's current `tools/list` before submission. Negative prompts should not invoke this plugin.

The 13 product packages are independently versioned at 1.0.1. Their listing and review source is `product-review.json`; `scripts/build_product_plugins.py` validates tool names against the dated discovery receipt and regenerates source packages, catalogs and OpenAI/Gemini ZIPs. Existing 1.0.0 downloads remain historical artifacts.

The dated `docs/plugins/review-tool-inventory-20261028.json` proves initialize and complete tool discovery only. It records negotiated protocol versions and missing annotations. It contains no tool-execution or model-acceptance claim. MyQuant App is metadata only. Trade Safety review cases inspect capabilities because live discovery does not specify the nested assessment input contract; they do not establish assessment acceptance. Market Corpus lacks tool annotation hints and remains a separate review gate. No real walkthrough recording has been attached.
