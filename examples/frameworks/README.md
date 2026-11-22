# Framework Quickstarts and Executable Colab Notebooks

Connect LiquiLens (bank and institution evidence + 12,301-entity ontology), Seiche (funding and money markets), Undertow (market and exit liquidity), and Palimpsest (China economic revisions and information controls) to any major AI agent framework without an API key.

## One-Click Google Colab Notebooks

| Notebook | Products | Open in Colab |
| --- | --- | --- |
| Indian Bank & SFB NPA / Capital Audit | LiquiLens | [Open in Colab](https://colab.research.google.com/github/beepboop2025/financial-evidence-skills/blob/main/notebooks/01_india_bank_npa_capital_audit.ipynb) |
| Financial Entity Resolution & Ontology Crosswalk | LiquiLens Ontology | [Open in Colab](https://colab.research.google.com/github/beepboop2025/financial-evidence-skills/blob/main/notebooks/02_financial_entity_ontology_crosswalk.ipynb) |
| USD Funding Stress & Exit Liquidity Packet | Seiche + Undertow | [Open in Colab](https://colab.research.google.com/github/beepboop2025/financial-evidence-skills/blob/main/notebooks/03_usd_funding_and_exit_liquidity.ipynb) |
| China Economy Revisions & Provenance Audit | Palimpsest | [Open in Colab](https://colab.research.google.com/github/beepboop2025/financial-evidence-skills/blob/main/notebooks/04_china_economy_revision_audit.ipynb) |

## Hosted Keyless MCP Endpoints

- LiquiLens: `https://agents.seiche.info/products/liquilens/mcp`
- Seiche: `https://agents.seiche.info/products/seiche/mcp`
- Undertow: `https://agents.seiche.info/products/undertow/mcp`
- Palimpsest: `https://agents.seiche.info/products/palimpsest/mcp`
- Financial Evidence Router: `https://agents.seiche.info/products/financial-evidence/mcp`

## Framework Examples

- [`openai_agents_mcp.py`](openai_agents_mcp.py): Connect the OpenAI Agents SDK to hosted Streamable HTTP MCP endpoints.
- [`pydantic_ai_mcp.py`](pydantic_ai_mcp.py): Connect PydanticAI agents to LiquiLens and Seiche over MCP.
- [`langchain_liquilens_tool.py`](langchain_liquilens_tool.py): Wrap the zero-key LiquiLens Ontology resolver and bank filing endpoint as LangChain / LangGraph tools.
- [`google_adk_mcp.py`](google_adk_mcp.py): Connect Google ADK / Gemini agents to the hosted read-only MCP endpoints.

## Evidence Boundary

Public research data only. Never use these examples to generate investment advice, trade recommendations, credit ratings, or execution instructions. Preserve source clocks, units, citations, and explicit unavailable states.
