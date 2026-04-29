"""Response builders for workflow outputs.

This keeps content-shaping details out of the main agent while leaving the
top-level orchestration and tool sequencing inside the main agent.
"""

from __future__ import annotations

from .specs import WorkflowSpec


def build_template_payload(
    *,
    spec: WorkflowSpec,
    user_input: str,
    findings: list[dict],
    grounding_note: str | None = None,
) -> dict[str, str]:
    source_lines = build_source_lines(findings, grounding_note=grounding_note)
    numbered_findings = build_numbered_findings(findings)
    first_title = findings[0]["title"] if findings else "the local documentation set"
    background = f"This document is generated to support the request: {user_input}"
    if grounding_note:
        background += f"\n\nGrounding note: {grounding_note}"

    common = {
        "title": user_input,
        "goal": user_input,
        "background": background,
        "sources": source_lines,
    }

    if spec.task_type == "tutorial_writing":
        return {
            **common,
            "audience": "UE developers who need a practical path from concept to implementation.",
            "prerequisites": "- Basic Unreal Editor familiarity\n- Ability to open the referenced docs\n- A project or sample scene for validation",
            "steps": numbered_findings,
            "example": f"Start with `{first_title}` as the anchor reference, then validate the steps in a small Blueprint or Editor prototype.",
            "faq": "- If the docs differ by engine version, note the target version before implementation.\n- If a step is unclear, inspect the referenced source path and replicate it in a small test scene.\n- If no valid sources were found, treat this draft as a planning scaffold rather than a grounded tutorial.",
        }

    if spec.task_type == "proposal_generation":
        return {
            **common,
            "user_scenarios": "- Developers building or evolving a UE feature\n- Teams needing a structured implementation direction\n- Stakeholders evaluating feasibility and constraints",
            "core_solution": numbered_findings,
            "structure_design": "- Organize the implementation around the retrieved engine concepts.\n- Separate editor UX, runtime logic, and content dependencies.\n- Keep the proposal traceable to the cited documentation.",
            "risks": "- Retrieved docs may reflect engine-version differences.\n- Integration cost depends on current project architecture and content pipeline.\n- If grounded references are missing, validate assumptions before treating this as a final proposal.",
            "implementation_advice": "- Start with a small prototype.\n- Validate editor/runtime boundaries early.\n- Convert the proposal into implementation tasks after scope review.",
        }

    return {
        **common,
        "phases": numbered_findings,
        "phase_outputs": "- Phase 1: clarified scope and success criteria\n- Phase 2: implementation or content outputs\n- Phase 3: review, validation, and iteration notes",
        "dependencies_and_risks": "- Team bandwidth and UE version alignment\n- Availability of project assets or test scenes\n- Need to validate assumptions against real project constraints\n- If no grounded references were found, treat this workflow as a draft scaffold.",
        "tools_and_resources": "- Unreal Editor\n- Local documentation search results\n- Team task tracker or planning board\n- Optional project examples if available later",
        "execution_advice": "- Keep each phase small enough to validate.\n- Convert key decisions into checklists.\n- Keep cited source paths in the working notes for traceability.",
    }


def render_direct_answer(
    *,
    spec: WorkflowSpec,
    user_input: str,
    findings: list[dict],
    grounding_note: str | None = None,
) -> str:
    top_titles = ", ".join(item["title"] for item in findings[:2]) or "the retrieved local docs"
    steps = build_short_steps(findings)
    sources = build_chat_sources(findings, limit=2, grounding_note=grounding_note)

    if spec.task_type == "proposal_generation":
        core_label = "## Core Recommendations"
        intro = f"For `{user_input}`, the safest recommendation is to base the proposal on {top_titles} and keep the scope narrow enough for an initial prototype."
    elif spec.task_type == "workflow_support":
        core_label = "## Core Path"
        intro = f"For `{user_input}`, start with a small phased workflow grounded in {top_titles}, then validate each phase with a lightweight test loop."
    else:
        core_label = "## Suggested Path"
        intro = f"A good starting path for `{user_input}` is to begin with {top_titles} and then validate the steps in a small UE example."

    return "\n".join(["## Direct Answer", intro, "", core_label, steps, "", "## References", sources])


def render_structured_chat(
    *,
    spec: WorkflowSpec,
    user_input: str,
    findings: list[dict],
    grounding_note: str | None = None,
) -> str:
    steps = build_numbered_findings(findings)
    sources = build_chat_sources(findings, limit=4, grounding_note=grounding_note)

    if spec.task_type == "proposal_generation":
        notes_title = "## Risks and Constraints"
        notes_body = "- Validate editor/runtime boundaries early.\n- Check engine-version dependencies before committing to implementation.\n- Keep the first version prototype-oriented."
        body_title = "## Recommended Direction"
    elif spec.task_type == "workflow_support":
        notes_title = "## Risks and Dependencies"
        notes_body = "- Confirm team ownership per phase.\n- Keep source material visible during review.\n- Validate assumptions in a small implementation loop."
        body_title = "## Suggested Phases"
    else:
        notes_title = "## Notes"
        notes_body = "- Keep the tutorial audience explicit.\n- Turn each retrieved concept into a practical exercise or checkpoint.\n- Call out version-specific caveats when validating the steps."
        body_title = "## Recommended Tutorial Structure"

    return "\n".join(["## Goal", user_input, "", body_title, steps, "", notes_title, notes_body, "", "## References", sources])


def render_chat_without_grounding(
    *,
    spec: WorkflowSpec,
    user_input: str,
    response_mode: str,
    grounding_note: str,
) -> str:
    if response_mode == "direct_answer":
        return "\n".join(
            [
                "## Direct Answer",
                f"I could not fully ground `{user_input}` against the current local documentation.",
                "",
                "## What You Can Do Next",
                "1. Narrow the query to a more specific UE subsystem, feature, or API.",
                "2. Include the target engine version, runtime/editor scope, or Blueprint/C++ context.",
                "3. Re-run the workflow after confirming the local docs index is available.",
                "",
                "## Grounding Status",
                f"- {grounding_note}",
                "",
                "## References",
                build_chat_sources([], limit=0, grounding_note=grounding_note),
            ]
        )

    return "\n".join(
        [
            "## Goal",
            user_input,
            "",
            "## Current Limitation",
            f"I could not ground this {spec.task_type.replace('_', ' ')} request against the local documentation.",
            "",
            "## Safe Next Steps",
            "1. Clarify the feature area, engine version, and desired output boundary.",
            "2. Re-run retrieval with narrower keywords.",
            "3. Treat any draft structure as a scaffold until grounded sources are available.",
            "",
            "## References",
            build_chat_sources([], limit=0, grounding_note=grounding_note),
        ]
    )


def build_short_steps(findings: list[dict]) -> str:
    lines: list[str] = []
    for index, item in enumerate(findings[:3], start=1):
        snippet = item.get("snippet") or "Use the referenced local documentation as the next step anchor."
        lines.append(f"{index}. {item['title']} - {snippet}")
    return "\n".join(lines) or "1. No grounded steps were available."


def build_numbered_findings(findings: list[dict]) -> str:
    lines: list[str] = []
    for index, item in enumerate(findings[:5], start=1):
        lines.append(f"{index}. {item['title']}")
        if item.get("snippet"):
            lines.append(f"   - {item['snippet']}")
    return "\n".join(lines) or "1. No grounded findings were available."


def build_source_lines(findings: list[dict], grounding_note: str | None = None) -> str:
    lines: list[str] = []
    for item in findings[:5]:
        title = item.get("title") or "Untitled source"
        path = item.get("path") or "No path provided"
        snippet = item.get("snippet") or ""
        lines.append(f"- {title}")
        lines.append(f"  - Path: {path}")
        if snippet:
            lines.append(f"  - Snippet: {snippet[:240]}")
    if grounding_note:
        lines.append(f"- Grounding status: {grounding_note}")
    return "\n".join(lines) or "- No validated sources were available for this draft."


def build_chat_sources(findings: list[dict], *, limit: int, grounding_note: str | None = None) -> str:
    lines: list[str] = []
    for item in findings[:limit]:
        title = item.get("title", "Untitled source")
        path = item.get("path", "No path provided")
        snippet = (item.get("snippet") or "").strip()
        lines.append(f"- {title}")
        lines.append(f"  - Path: {path}")
        if snippet:
            lines.append(f"  - Snippet: {snippet[:180]}")
    if grounding_note:
        lines.append(f"- Grounding status: {grounding_note}")
    return "\n".join(lines) or "- No validated sources were available."
