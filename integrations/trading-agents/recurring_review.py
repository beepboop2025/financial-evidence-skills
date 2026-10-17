"""Application-owned recurring review hook. Importing performs no network read.

The returned function works directly or as a synchronous LangGraph node.
Configure its directory, workflow and mode in application code, not model inputs.
"""
from financial_evidence.agent_workflow import AgentWorkflow


def review_node(directory, *, workflow="funding", selection="USD", mode="unknown"):
    journal = AgentWorkflow(directory, mode=mode)

    def review(_state):
        return {"financial_review": journal.run(workflow, selection)}

    return review


if __name__ == "__main__":
    import sys
    from financial_evidence.cli import main
    raise SystemExit(main(["workflow", *sys.argv[1:]]))
