"""Workflow selection helpers.

The selector stays heuristic and readable, but pulls workflow-specific
keywords and markers from workflow specs instead of hardcoding them in the agent.
"""

from __future__ import annotations

from dataclasses import dataclass

from .specs import WorkflowSpec, list_workflow_specs


@dataclass(frozen=True)
class WorkflowMatch:
    spec: WorkflowSpec
    score: int
    has_primary_marker: bool


def resolve_workflow_intent(user_input: str) -> WorkflowMatch | None:
    lower = user_input.lower()
    matches: list[WorkflowMatch] = []

    for spec in list_workflow_specs():
        score = sum(1 for keyword in spec.intent_keywords if keyword in lower or keyword in user_input)
        has_primary_marker = any(marker in lower or marker in user_input for marker in spec.primary_markers)
        matches.append(WorkflowMatch(spec=spec, score=score, has_primary_marker=has_primary_marker))

    if not matches:
        return None

    best = max(matches, key=lambda item: item.score)
    if best.score < 2 and not best.has_primary_marker:
        return None
    return best
