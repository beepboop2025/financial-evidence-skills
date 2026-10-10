"""Bounded native research-tool examples. No model key, orders, or background jobs."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from financial_evidence.agents import EvidenceAgentClient, framework_tools
from forward_evidence import capture, save


def langgraph_review(client: EvidenceAgentClient, entity: str = "USD", limit: int = 5) -> dict:
    """Run a real LangGraph tool node with one explicit read-only call."""
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph
    from langgraph.prebuilt import ToolNode

    tools = framework_tools("langchain", client)
    query = next(tool for tool in tools if tool.name == "financial_evidence_query")
    builder = StateGraph(MessagesState)
    builder.add_node("funding_evidence", ToolNode([query]))
    builder.add_edge(START, "funding_evidence")
    builder.add_edge("funding_evidence", END)
    graph = builder.compile()
    result = graph.invoke({"messages": [AIMessage(content="", tool_calls=[{
        "name": query.name, "args": {"dataset": "money_markets", "entity": entity, "limit": limit},
        "id": "bounded-funding-review", "type": "tool_call",
    }])]})
    message = result["messages"][-1]
    if getattr(message, "status", "success") == "error":
        raise RuntimeError("The native LangGraph evidence tool returned an error")
    return capture(json.loads(message.content))


def crewai_review(client: EvidenceAgentClient, entity: str = "USD", limit: int = 5) -> dict:
    """Invoke CrewAI's native tool; attach the same tool to your own researcher."""
    tools = framework_tools("crewai", client)
    query = next(tool for tool in tools if tool.name == "financial_evidence_query")
    packet = query.run(dataset="money_markets", entity=entity, limit=limit)
    return capture(packet)


def tradingagents_funding_tool(client: EvidenceAgentClient):
    """Local analyst extension using TradingAgents' LangChain tool interface.

    Register it in the analyst model and matching ToolNode. Existing historical
    ``trade_date`` runs fail before fetching evidence; current context must never
    masquerade as a point-in-time historical provider.
    """
    from langchain_core.tools import tool

    @tool
    def get_forward_funding_context(trade_date: str, entity: str = "USD") -> dict:
        """Current UTC-date funding research only. Not security prices or a trade signal.

        Historical/future trade dates are rejected. Cite the complete source rows,
        event_time, available_at, units and gaps; this grants no execution authority.
        """
        requested = date.fromisoformat(trade_date)
        if trade_date != requested.isoformat() or requested != datetime.now(timezone.utc).date():
            raise ValueError("Only the current UTC date is supported; historical TradingAgents runs are refused")
        return capture(client.query("money_markets", entity=entity, limit=5))

    return get_forward_funding_context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("framework", choices=["langgraph", "crewai", "tradingagents"])
    parser.add_argument("--entity", default="USD")
    parser.add_argument("--output", type=Path, required=True, help="New capture folder")
    args = parser.parse_args()
    with EvidenceAgentClient() as client:
        if args.framework == "langgraph":
            snapshot = langgraph_review(client, args.entity)
        elif args.framework == "crewai":
            snapshot = crewai_review(client, args.entity)
        else:
            snapshot = tradingagents_funding_tool(client).invoke({
                "trade_date": datetime.now(timezone.utc).date().isoformat(), "entity": args.entity})
    print(json.dumps(save(snapshot, args.output), indent=2))
    return 0 if snapshot["packet"]["transport_status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
