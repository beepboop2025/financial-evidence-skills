"""Private product-improvement summaries from enrolled, content-free events."""
from collections import Counter, defaultdict

from . import contracts as c

ELIGIBLE_MODES = frozenset({"shadow", "paper", "operator_reported_production"})


def _groups(events):
    groups = {}
    excluded = Counter()
    for owner, event in events:
        if event["mode"] not in ELIGIBLE_MODES:
            excluded[event["mode"]] += 1
            continue
        key = (owner, event["product"], event["task"], event["mode"],
               event.get("logical_workflow_id", event["id"]))
        group = groups.setdefault(key, {
            "attempts": [], "feedback": [], "useful": set(), "reasons": set(), "gaps": set(),
        })
        group["feedback" if c.is_feedback(event) else "attempts"].append(event)
        if "useful" in event:
            group["useful"].add(event["useful"])
        if "feedback_reason" in event:
            group["reasons"].add(event["feedback_reason"])
        group["gaps"].update(event.get("data_gaps", []))
    return groups, excluded


def confirmed_workflows(events):
    """Use observed successful-attempt times, never delayed rating times."""
    groups, _ = _groups(events)
    confirmed = []
    for key, group in groups.items():
        successful = [event for event in group["attempts"] if event["status"] == "success"]
        if group["useful"] == {True} and successful:
            confirmed.append((key[0], min(successful, key=lambda event: (event["occurred_at"], event["id"]))))
    return confirmed


def summarize(events):
    """Aggregate (workspace, validated event) pairs; never emit workspace IDs.

    Repeated feedback cannot inflate affected-workflow/workspace counts.
    Conflicting usefulness reports stay unknown. Feedback-only submissions
    remain visible without manufacturing an observed request or completion.
    """
    groups, excluded = _groups(events)

    breakdown = defaultdict(list)
    issues = defaultdict(set)
    gaps = defaultdict(set)
    for key, group in groups.items():
        breakdown[key[1:3]].append((key, group))
        for reason in group["reasons"]:
            issues[(key[1], key[2], "feedback", reason)].add(key)
        for event in group["attempts"]:
            if event["status"] != "success":
                reason = event.get("failure_reason", "unspecified_" + event["status"])
                issues[(key[1], key[2], "attempt", reason)].add(key)
        for gap in group["gaps"]:
            gaps[(key[1], key[2], "requested_data", gap)].add(key)

    def counts(selected):
        observed = [group for _, group in selected if group["attempts"]]
        answered = [group for group in observed if group["useful"]]
        useful = [group for group in answered if group["useful"] == {True}
                  and any(event["status"] == "success" for event in group["attempts"])]
        feedback_only = [group for _, group in selected if not group["attempts"]]
        return {
            "observed_workflows": len(observed),
            "observed_attempts": sum(len(group["attempts"]) for group in observed),
            "feedback_submissions": sum(len(group["feedback"]) for _, group in selected),
            "workflows_with_feedback": len(answered),
            "workflows_without_feedback": len(observed) - len(answered),
            "feedback_coverage": len(answered) / len(observed) if observed else None,
            "confirmed_useful_workflows": len(useful),
            "not_useful_workflows": sum(group["useful"] == {False} for group in answered),
            "conflicting_feedback_workflows": sum(len(group["useful"]) > 1 for group in answered),
            "feedback_only_workflows": len(feedback_only),
            "feedback_only_reported_useful": sum(group["useful"] == {True} for group in feedback_only),
        }

    def ranked(buckets):
        rows = [{
            "product": product, "task": task, "signal": signal, "category": category,
            "affected_workflows": len(keys), "affected_workspaces": len({key[0] for key in keys}),
        } for (product, task, signal, category), keys in buckets.items()]
        return sorted(rows, key=lambda row: (
            -row["affected_workspaces"], -row["affected_workflows"],
            row["product"], row["task"], row["signal"], row["category"],
        ))

    return {
        "schema": "financial-evidence.product-learning.v1",
        "scope": "retained enrolled measurement only; workspaces are not verified people or organisations",
        "usefulness_is_operator_reported": True,
        "missing_feedback_is_unknown": True,
        "priority_order": "affected workspaces, then affected workflows, then stable category order",
        "data_requests_grant_source_access": False,
        "excluded_events_by_mode": dict(sorted(excluded.items())),
        **counts(list(groups.items())),
        "by_product_task": [
            {"product": product, "task": task, **counts(selected)}
            for (product, task), selected in sorted(breakdown.items())
        ],
        "recurring_problems": ranked(issues),
        "requested_data": ranked(gaps),
    }
