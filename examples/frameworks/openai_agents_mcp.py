"""OpenAI Agents SDK example using hosted keyless LiquiLens and Seiche MCP endpoints.

Install:
    pip install openai-agents

Usage:
    export OPENAI_API_KEY=...
    python examples/frameworks/openai_agents_mcp.py
"""
from __future__ import annotations

import asyncio

LIQUILENS_MCP_URL = "https://agents.seiche.info/products/liquilens/mcp"
SEICHE_MCP_URL = "https://agents.seiche.info/products/seiche/mcp"


async def main() -> None:
    from agents import Agent, Runner
    from agents.mcp import MCPServerStreamableHttp

    async with (
        MCPServerStreamableHttp(name="liquilens", params={"url": LIQUILENS_MCP_URL}) as liquilens,
        MCPServerStreamableHttp(name="seiche", params={"url": SEICHE_MCP_URL}) as seiche,
    ):
        analyst = Agent(
            name="Financial Evidence Analyst",
            instructions=(
                "Use LiquiLens for institution filings and ontology IDs, and Seiche for funding context. "
                "Keep separate sections with observation dates, units, and explicit missingness. "
                "Do not give investment advice or credit ratings."
            ),
            mcp_servers=[liquilens, seiche],
        )
        result = await Runner.run(
            analyst,
            "Resolve Cosmos Co-operative Bank in LiquiLens and summarize current USD funding context from Seiche.",
        )
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
