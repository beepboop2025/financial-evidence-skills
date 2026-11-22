"""Google ADK / Gemini agent configuration for hosted keyless Financial Evidence MCP servers.

Install:
    pip install google-adk

Reference:
    https://liquilens.in/agents/
"""
from __future__ import annotations

MCP_ENDPOINTS = {
    "liquilens": "https://agents.seiche.info/products/liquilens/mcp",
    "seiche": "https://agents.seiche.info/products/seiche/mcp",
    "undertow": "https://agents.seiche.info/products/undertow/mcp",
}


def create_adk_agent():
    """Create a Google ADK LlmAgent attached to read-only Financial Evidence MCP servers."""
    from google.adk.agents import LlmAgent
    from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

    toolsets = [
        MCPToolset(connection_params=StreamableHTTPConnectionParams(url=url))
        for url in MCP_ENDPOINTS.values()
    ]
    return LlmAgent(
        model="gemini-2.5-pro",
        name="financial_evidence_researcher",
        instruction=(
            "Use LiquiLens for institution filings and ontology lookup, Seiche for funding context, "
            "and Undertow for exit liquidity. Keep clocks, units, and explicit gaps intact. "
            "Public research only, never investment advice."
        ),
        tools=toolsets,
    )
