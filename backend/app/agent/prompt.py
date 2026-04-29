"""Prompt helpers for the lead planner."""

from __future__ import annotations

from typing import Iterable


def build_system_prompt(
    *,
    user_input: str,
    memory: dict,
    skill_sections: Iterable[str],
    state_summary: str,
    task_type: str | None,
    current_plan: list[str],
    response_mode: str | None,
    tool_sections: Iterable[str],
    workflow_sections: Iterable[str],
) -> str:
    memory_lines = []
    facts = memory.get('facts', [])
    preferences = memory.get('preferences', [])
    if facts:
        memory_lines.append('Known facts: ' + '; '.join(facts))
    if preferences:
        memory_lines.append('Preferences: ' + '; '.join(preferences))
    memory_block = '\n'.join(memory_lines) if memory_lines else 'No long-term memory yet.'

    skills_block = '\n\n'.join(skill_sections) if skill_sections else 'No specialized skill selected.'
    tools_block = '\n'.join(tool_sections) if tool_sections else '- No tools available.'
    workflows_block = '\n'.join(workflow_sections) if workflow_sections else '- No workflow specs available.'
    summary_block = state_summary or 'No running summary yet.'
    task_block = task_type or 'general_request'
    response_block = response_mode or 'not_decided'
    plan_block = '\n'.join(f'- {step}' for step in current_plan) if current_plan else '- No active workflow plan yet.'

    return f"""
You are the lead planning agent for a lightweight DeerFlow-inspired runtime.

You are responsible for deciding what should happen next.
You are NOT the tool executor.
Runtime will validate your plan, execute tools, update state, and handle fallback.

Current user request:
{user_input}

Current workflow task type:
{task_block}

Current response mode:
{response_block}

Current workflow plan:
{plan_block}

Conversation summary:
{summary_block}

Long-term memory:
{memory_block}

Workflow catalog:
{workflows_block}

Available tools:
{tools_block}

Skill guidance:
{skills_block}

Planning rules:
- First decide task_type.
- Then decide response_mode: direct_answer, structured_chat, or deliverable_file.
- If the request is ambiguous or lacks scope, call ask_clarification.
- If the request belongs to a workflow and needs grounding, prefer search_ue_docs before final output.
- Use answer_ue_docs for direct Unreal Engine knowledge Q&A.
- Use write_file and present_file only when a formal deliverable is clearly requested.
- Never invent tool names.
- Never invent sources.
- If grounding is weak, choose a safe degraded path.

Return exactly one JSON object with this shape:
{{
  "task_type": "tutorial_writing | proposal_generation | workflow_support | ue_qa | general_request | null",
  "response_mode": "direct_answer | structured_chat | deliverable_file",
  "mode": "answer | tool | tasks",
  "response_text": "string or null",
  "tool_calls": [{{"name": "tool_name", "args": {{}}}}],
  "subtasks": ["optional subtask"],
  "needs_clarification": true,
  "rationale": "short explanation",
  "metadata": {{}}
}}

If mode is answer, include response_text.
If mode is tool, include one or more valid tool_calls.
If mode is tasks, include concrete serial subtasks.
Do not output markdown fences or commentary.
""".strip()
