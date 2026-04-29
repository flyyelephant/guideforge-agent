"""Runtime guardrails for planner output.

The planner is allowed to think at a high level, but runtime still owns
legality, safety, and execution constraints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .state import AgentState
from ..routing.heuristics import general_clarification_question, needs_file_output, needs_workflow_clarification
from ..runtime.types import ModelDecision, ToolCall
from ..tools.base import BaseTool
from ..workflows.specs import get_workflow_spec

_VALID_RESPONSE_MODES = {'direct_answer', 'structured_chat', 'deliverable_file'}
_VALID_MODES = {'answer', 'tool', 'tasks'}
_ALLOWED_NON_WORKFLOW_TASKS = {'ue_qa', 'general_request', None}


@dataclass
class GuardrailResult:
    decision: ModelDecision
    actions: list[str] = field(default_factory=list)
    fallback_used: bool = False
    fallback_reason: str | None = None


class DecisionGuardrails:
    """Validate, repair, or fall back on planner output before execution."""

    def __init__(self, *, fallback_model: Any) -> None:
        self.fallback_model = fallback_model

    def validate(
        self,
        *,
        decision: ModelDecision,
        user_input: str,
        state: AgentState,
        tools: Iterable[BaseTool],
        system_prompt: str,
    ) -> GuardrailResult:
        actions: list[str] = []
        tool_map = {tool.name: tool for tool in tools}

        if decision.mode not in _VALID_MODES:
            return self._fallback('Planner returned an invalid mode.', user_input, state, tools, system_prompt, actions)

        task_type = decision.metadata.get('task_type')
        spec = get_workflow_spec(str(task_type)) if task_type else None
        heuristic_task_type = self.fallback_model.classify_task(user_input)
        heuristic_spec = get_workflow_spec(str(heuristic_task_type)) if heuristic_task_type else None
        if task_type not in _ALLOWED_NON_WORKFLOW_TASKS and spec is None:
            actions.append(f"Unknown task_type '{task_type}' was dropped.")
            task_type = None
            spec = None

        if heuristic_spec is not None and (spec is None or task_type in _ALLOWED_NON_WORKFLOW_TASKS):
            task_type = heuristic_task_type
            spec = heuristic_spec
            actions.append(f"Workflow task_type repaired from heuristic bootstrap: '{task_type}'.")

        response_mode = decision.metadata.get('response_mode')
        if response_mode not in _VALID_RESPONSE_MODES:
            repaired_mode = self.fallback_model.classify_response_mode(user_input, task_type)
            actions.append(f"Invalid response_mode repaired to '{repaired_mode}'.")
            response_mode = repaired_mode

        if response_mode == 'deliverable_file' and spec is None and not needs_file_output(user_input):
            actions.append('deliverable_file was downgraded to structured_chat for a non-workflow request.')
            response_mode = 'structured_chat'

        if decision.mode == 'tool':
            tool_calls = self._sanitize_tool_calls(decision.tool_calls, tool_map, spec, actions)
            if not tool_calls:
                return self._fallback('Planner produced no valid tool calls.', user_input, state, tools, system_prompt, actions)
            if spec is not None and len(tool_calls) == 1 and tool_calls[0].name == 'ask_clarification' and not needs_workflow_clarification(user_input):
                tool_calls = [ToolCall(name='search_ue_docs', args={'query': user_input, 'top_k': 5})]
                actions.append('Unnecessary workflow clarification was replaced with search_ue_docs grounding.')
            decision.tool_calls = tool_calls

        if decision.mode == 'tasks':
            decision.subtasks = [item for item in decision.subtasks if item]
            if not decision.subtasks:
                return self._fallback('Planner requested task mode without subtasks.', user_input, state, tools, system_prompt, actions)

        if decision.mode == 'answer' and spec is not None:
            actions.append('Workflow answer was converted into grounded search_ue_docs planning.')
            decision.mode = 'tool'
            decision.tool_calls = [ToolCall(name='search_ue_docs', args={'query': user_input, 'top_k': 5})]
            decision.response_text = None

        if decision.mode == 'answer' and not (decision.response_text or '').strip():
            return self._fallback('Planner answer mode did not include response_text.', user_input, state, tools, system_prompt, actions)

        metadata = dict(decision.metadata)
        metadata['task_type'] = task_type
        metadata['response_mode'] = response_mode
        metadata['workflow_hit'] = spec is not None
        if spec is not None:
            metadata['plan'] = list(spec.default_plan)
            metadata['template_name'] = spec.template_name
            metadata['filename_prefix'] = spec.filename_prefix
            metadata['compose_document'] = response_mode == 'deliverable_file'
        else:
            metadata.pop('template_name', None)
            metadata.pop('filename_prefix', None)
            metadata['compose_document'] = False
        decision.metadata = metadata
        return GuardrailResult(decision=decision, actions=actions)

    def _sanitize_tool_calls(
        self,
        tool_calls: list[ToolCall],
        tool_map: dict[str, BaseTool],
        spec,
        actions: list[str],
    ) -> list[ToolCall]:
        sanitized: list[ToolCall] = []
        for call in tool_calls:
            if call.name not in tool_map:
                actions.append(f"Unknown tool '{call.name}' was removed.")
                continue
            args = call.args if isinstance(call.args, dict) else {}
            if call.name == 'ask_clarification':
                if 'question' not in args or not str(args.get('question', '')).strip():
                    args = {'question': spec.clarification_question if spec is not None else general_clarification_question()}
                    actions.append('Clarification tool call was repaired with a default question.')
            sanitized.append(ToolCall(name=call.name, args=args))

        if spec is not None:
            names = [call.name for call in sanitized]
            if 'ask_clarification' not in names and 'search_ue_docs' not in names:
                sanitized.insert(0, ToolCall(name='search_ue_docs', args={'query': '', 'top_k': 5}))
                actions.append('Workflow decision was prepended with search_ue_docs for grounding.')
        return sanitized

    def _fallback(
        self,
        reason: str,
        user_input: str,
        state: AgentState,
        tools: Iterable[BaseTool],
        system_prompt: str,
        actions: list[str],
    ) -> GuardrailResult:
        fallback_decision = self.fallback_model.decide(user_input, state, tools, system_prompt)
        actions.append(f'Heuristic fallback activated: {reason}')
        return GuardrailResult(
            decision=fallback_decision,
            actions=actions,
            fallback_used=True,
            fallback_reason=reason,
        )
