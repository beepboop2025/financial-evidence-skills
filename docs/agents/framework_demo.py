#!/usr/bin/env python3
"""Register native financial research tools without a model key or LLM call."""
import argparse
import json
from financial_evidence.agents import EvidenceAgentClient, framework_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("framework", choices=["langchain", "crewai", "openai", "pydantic-ai"])
    parser.add_argument("--live", action="store_true", help="Fetch a bounded research review after registration")
    args = parser.parse_args()
    with EvidenceAgentClient() as client:
        tools = framework_tools(args.framework, client)
        print(json.dumps({"framework": args.framework, "tools": [tool.name for tool in tools]}))
        if args.live:
            print(json.dumps(client.review(limit=3), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
