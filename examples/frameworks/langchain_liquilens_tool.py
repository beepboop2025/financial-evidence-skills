"""LangChain / LangGraph zero-key tools for LiquiLens Ontology and bank filings.

Install:
    pip install langchain-core

Can be imported and tested without any LLM key; only the live HTTP call hits api.liquilens.in.
"""
from __future__ import annotations

import json
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE_API = "https://api.liquilens.in/api/experimental/v1"


def resolve_financial_entity(query: str) -> dict:
    """Resolve a bank name, CIN, LEI, or district to its canonical LiquiLens ontology ID."""
    url = f"{BASE_API}/ontology/resolve?q={quote(query)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "LangChain-LiquiLens-Example/1.0"})
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_indian_bank_filings(slug: str) -> dict:
    """Retrieve dated public NPA, capital, and CASA disclosures for a covered Indian bank slug."""
    url = f"{BASE_API}/banking/institutions/{quote(slug)}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "LangChain-LiquiLens-Example/1.0"})
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_langchain_tools():
    """Return LangChain StructuredTool wrappers for LiquiLens public endpoints."""
    from langchain_core.tools import tool

    return [
        tool(resolve_financial_entity),
        tool(fetch_indian_bank_filings),
    ]


if __name__ == "__main__":
    print(json.dumps(resolve_financial_entity("Cosmos Co-operative Bank"), indent=2))
