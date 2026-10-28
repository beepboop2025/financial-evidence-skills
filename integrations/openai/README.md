# OpenAI review packages

The Financial Evidence OpenAI ZIP is independently versioned at 0.1.17. Its source manifest is `financial-evidence/plugin.json`; the Python, container, Claude and root Codex release remain 0.1.16. This candidate changes listing text and review metadata only, retaining the same seven runtime assets and MCP connection.

Run `python3 scripts/build_openai_submission.py` to regenerate the ZIP and content receipt, or add `--check` to verify committed bytes. Review cases describe expected behavior; they are not model-run results or directory approval. The walkthrough video has not been recorded, so no demo URL is declared.

The manifest follows https://developers.openai.com/plugins/deploy/submission. Review cases must contain exactly five positive and three negative cases. Positive tool names must be checked against the hosted server's current `tools/list` before submission. Negative prompts should not invoke this plugin.
