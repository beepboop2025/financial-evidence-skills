"""PydanticAI example connecting to hosted keyless LiquiLens and Undertow MCP endpoints.

Install:
    pip install pydantic-ai

Usage:
    export OPENAI_API_KEY=...  # or ANTHROPIC_API_KEY / GEMINI_API_KEY
    python examples/frameworks/pydantic_ai_mcp.py
"""
from __future__ import annotations

import asyncio

LIQUILENS_MCP_URL = "https://agents.seiche.info/products/liquilens/mcp"
UNDERTOW_MCP_URL = "https://agents.seiche.info/products/undertow/mcp"


async def main() -> None:
    from pydantic_ai import Agent
    from pydantic_ai.mcp import MCPServerStreamableHTTP

    liquilens = MCPServerStreamableHTTP(LIQUILENS_MCP_URL)
    undertow = MCPServerStreamableHTTP(UNDERTOW_MCP_URL)

    agent = Agent(
        "openai:gpt-4.1-mini",
        toolsets=[liquilens, undertow],
        system_prompt=(
            "Retrieve dated public research from LiquiLens and Undertow. "
            "Keep each product's clocks and missing disclosures explicit. "
            "Never average scores or provide trade advice."
        ),
    )
    async with agent:
        result = await agent.run(
            "Check filed metrics for Suryoday Small Finance Bank and summarize current Undertow liquidity segments."
        )
        print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
