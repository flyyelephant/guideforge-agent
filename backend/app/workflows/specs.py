"""Lightweight workflow specifications.

This module keeps workflow metadata out of the main agent so new workflow types
can be added with mostly declarative changes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowSpec:
    task_type: str
    skill_key: str
    template_name: str
    filename_prefix: str
    default_plan: list[str]
    clarification_question: str
    intent_keywords: list[str]
    primary_markers: list[str]
    default_response_mode: str = "structured_chat"


WORKFLOW_SPECS: dict[str, WorkflowSpec] = {
    "tutorial_writing": WorkflowSpec(
        task_type="tutorial_writing",
        skill_key="tutorial_writing_skill",
        template_name="tutorial",
        filename_prefix="tutorial",
        default_plan=[
            "Clarify the tutorial topic, audience, and expected learning outcome.",
            "Search UE docs for grounded concepts, steps, and examples.",
            "Choose the right response mode: direct answer, structured chat, or file deliverable.",
            "Only write a markdown artifact when the user explicitly wants a formal deliverable.",
        ],
        clarification_question="Please share the tutorial topic, target audience, and expected learning outcome.",
        intent_keywords=["tutorial", "guide", "walkthrough", "??", "??", "??", "how to", "??", "???", "????", "????", "??", "???"],
        primary_markers=["tutorial", "??", "guide", "??", "???"],
        default_response_mode="structured_chat",
    ),
    "proposal_generation": WorkflowSpec(
        task_type="proposal_generation",
        skill_key="proposal_generation_skill",
        template_name="proposal",
        filename_prefix="proposal",
        default_plan=[
            "Clarify the scope, users, and constraints of the proposal.",
            "Search UE docs for relevant engine capabilities and limitations.",
            "Choose the right response mode: direct answer, structured chat, or file deliverable.",
            "Only write a markdown proposal when the user explicitly wants a formal deliverable.",
        ],
        clarification_question="Please share the proposal topic, target users, scope boundaries, and constraints.",
        intent_keywords=["proposal", "design", "architecture", "solution", "方案", "设计", "规划"],
        primary_markers=["proposal", "方案", "solution"],
        default_response_mode="structured_chat",
    ),
    "workflow_support": WorkflowSpec(
        task_type="workflow_support",
        skill_key="workflow_support_skill",
        template_name="workflow",
        filename_prefix="workflow",
        default_plan=[
            "Clarify the team context, target outcome, and delivery constraints.",
            "Search UE docs for supporting methods and engine guidance.",
            "Choose the right response mode: direct answer, structured chat, or file deliverable.",
            "Only write a workflow document when the user explicitly wants a formal deliverable.",
        ],
        clarification_question="Please share the workflow topic, team context, time horizon, and expected deliverable.",
        intent_keywords=["workflow", "pipeline", "flow", "process", "流程", "工作流", "步骤", "phase"],
        primary_markers=["workflow", "流程", "工作流"],
        default_response_mode="structured_chat",
    ),
}


def get_workflow_spec(task_type: str) -> WorkflowSpec | None:
    return WORKFLOW_SPECS.get(task_type)


def list_workflow_specs() -> list[WorkflowSpec]:
    return list(WORKFLOW_SPECS.values())
