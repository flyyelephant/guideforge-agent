"""Main agent orchestration loop."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .decision_guardrails import DecisionGuardrails
from .llm_planner import LLMPlanner, PlannerOutputError, PlannerUnavailableError
from .prompt import build_system_prompt
from .response_helpers import build_fallback_direct_answer, build_fallback_document
from .state import AgentState
from ..memory.store import MemoryStore
from ..memory.updater import update_memory_from_text
from ..middleware.base import MiddlewareManager
from ..prompts.template_loader import read_template
from ..routing.heuristics import (
    build_subtasks,
    classify_response_mode,
    general_clarification_question,
    needs_file_output,
    needs_general_clarification,
    needs_task_split,
    needs_workflow_clarification,
    should_use_answer_ue_docs,
    should_use_rag,
    should_use_search,
)
from ..runtime.types import AgentResponse, ModelDecision, ToolCall, ToolResult
from ..skills.loader import select_skill_sections
from ..tools.base import BaseTool
from ..tools.registry import ToolRegistry
from ..workflows.renderers import (
    build_template_payload,
    render_chat_without_grounding,
    render_direct_answer,
    render_structured_chat,
)
from ..workflows.tutorial_authoring import assess_tutorial_grounding, build_tutorial_retry_query, get_tutorial_authoring_service
from ..workflows.selector import WorkflowMatch, resolve_workflow_intent
from ..workflows.specs import WorkflowSpec, get_workflow_spec, list_workflow_specs


@dataclass
class HeuristicModel:
    """Fallback planning layer.

    The runtime now prefers an LLM lead planner, but the heuristic planner stays
    in place as a safe fallback and repair path when model output is unavailable
    or invalid.
    """

    def classify_task(self, user_input: str) -> str | None:
        match = resolve_workflow_intent(user_input)
        return match.spec.task_type if match else None

    def classify_response_mode(self, user_input: str, task_type: str | None) -> str:
        spec = get_workflow_spec(task_type) if task_type else None
        default_mode = spec.default_response_mode if spec else None
        return classify_response_mode(user_input, task_type, default_workflow_mode=default_mode)

    def decide(self, user_input: str, state: AgentState, tools: Iterable[BaseTool], system_prompt: str) -> ModelDecision:
        workflow_match = resolve_workflow_intent(user_input)
        task_type = workflow_match.spec.task_type if workflow_match else None
        response_mode = self.classify_response_mode(user_input, task_type)

        if workflow_match and needs_workflow_clarification(user_input):
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='ask_clarification', args={'question': workflow_match.spec.clarification_question})],
                rationale='Structured workflow request is missing scope information.',
                metadata=self._workflow_metadata(workflow_match, response_mode),
            )

        if needs_general_clarification(user_input):
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='ask_clarification', args={'question': general_clarification_question()})],
                rationale='Request is too ambiguous to execute safely.',
                metadata={'response_mode': response_mode, 'task_type': 'general_request'},
            )

        if workflow_match:
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='search_ue_docs', args={'query': user_input, 'top_k': 5})],
                rationale='Workflow tasks should be grounded with UE docs search before choosing the final response format.',
                metadata=self._workflow_metadata(workflow_match, response_mode),
            )

        if should_use_answer_ue_docs(user_input):
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='answer_ue_docs', args={'query': user_input, 'top_k': 5})],
                rationale='Direct UE knowledge question.',
                metadata={'task_type': 'ue_qa', 'response_mode': response_mode},
            )

        if needs_task_split(user_input):
            return ModelDecision(
                mode='tasks',
                subtasks=build_subtasks(user_input),
                rationale='Complex request benefits from serial decomposition.',
                metadata={'response_mode': response_mode, 'task_type': 'general_request'},
            )

        if needs_file_output(user_input):
            content = build_fallback_document(user_input, state)
            return ModelDecision(
                mode='tool',
                tool_calls=[
                    ToolCall(name='write_file', args={'path': 'agent_output.md', 'content': content}),
                    ToolCall(name='present_file', args={'path': 'agent_output.md'}),
                ],
                rationale='User explicitly requested a file artifact.',
                metadata={'response_mode': 'deliverable_file', 'task_type': 'general_request'},
            )

        if should_use_search(user_input):
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='search', args={'query': user_input})],
                rationale='Search-style request.',
                metadata={'response_mode': response_mode, 'task_type': 'general_request'},
            )

        if should_use_rag(user_input):
            return ModelDecision(
                mode='tool',
                tool_calls=[ToolCall(name='rag', args={'query': user_input})],
                rationale='Local runtime knowledge request.',
                metadata={'response_mode': response_mode, 'task_type': 'general_request'},
            )

        return ModelDecision(
            mode='answer',
            response_text=build_fallback_direct_answer(user_input, state),
            rationale='Handled directly.',
            metadata={'response_mode': response_mode, 'task_type': 'general_request'},
        )

    def _workflow_metadata(self, workflow_match: WorkflowMatch, response_mode: str) -> dict[str, object]:
        spec = workflow_match.spec
        return {
            'task_type': spec.task_type,
            'response_mode': response_mode,
            'plan': list(spec.default_plan),
            'template_name': spec.template_name,
            'filename_prefix': spec.filename_prefix,
            'compose_document': response_mode == 'deliverable_file',
        }


class MainAgent:
    """Coordinates lead planning, tool execution, middleware, skills, and memory."""

    def __init__(
        self,
        *,
        planner: LLMPlanner,
        fallback_model: HeuristicModel,
        guardrails: DecisionGuardrails,
        tool_registry: ToolRegistry,
        middleware_manager: MiddlewareManager,
        memory_store: MemoryStore,
    ) -> None:
        self.planner = planner
        self.fallback_model = fallback_model
        self.guardrails = guardrails
        self.tool_registry = tool_registry
        self.middleware_manager = middleware_manager
        self.memory_store = memory_store

    def run(self, user_input: str, state: AgentState) -> AgentResponse:
        state.add_message('user', user_input)
        state.context['last_user_intent'] = user_input
        self.middleware_manager.before_agent(state, user_input)

        bootstrap_task_type = self.fallback_model.classify_task(user_input)
        bootstrap_response_mode = self.fallback_model.classify_response_mode(user_input, bootstrap_task_type)
        memory = self.memory_store.get_memory(state.runtime['user_id'])
        skill_sections = select_skill_sections(user_input, bootstrap_task_type, bootstrap_response_mode)
        system_prompt = build_system_prompt(
            user_input=user_input,
            memory=memory,
            skill_sections=skill_sections,
            state_summary=state.context.get('conversation_summary', ''),
            task_type=state.task_type or bootstrap_task_type,
            current_plan=state.plan,
            response_mode=state.response_mode or bootstrap_response_mode,
            tool_sections=self._describe_tools(self.tool_registry.list_tools()),
            workflow_sections=self._describe_workflows(),
        )

        decision, planner_debug = self._plan_decision(
            user_input=user_input,
            state=state,
            system_prompt=system_prompt,
            bootstrap_task_type=bootstrap_task_type,
            bootstrap_response_mode=bootstrap_response_mode,
        )
        state.context['planner_debug'] = planner_debug
        self._apply_decision_state(state, decision)
        early_response = self.middleware_manager.after_model(state, decision)
        if early_response is not None:
            state.add_message('assistant', early_response.output_text, status=early_response.status)
            self.middleware_manager.after_agent(state, early_response)
            update_memory_from_text(self.memory_store, state.runtime['user_id'], user_input)
            return early_response

        response = self._execute_decision(decision, state, user_input)
        state.add_message('assistant', response.output_text, status=response.status)
        response = self.middleware_manager.after_agent(state, response) or response
        update_memory_from_text(self.memory_store, state.runtime['user_id'], user_input)
        return response

    def _plan_decision(
        self,
        *,
        user_input: str,
        state: AgentState,
        system_prompt: str,
        bootstrap_task_type: str | None,
        bootstrap_response_mode: str,
    ) -> tuple[ModelDecision, dict[str, object]]:
        planner_debug: dict[str, object] = {
            'bootstrap_task_type': bootstrap_task_type,
            'bootstrap_response_mode': bootstrap_response_mode,
            'planner_source': 'llm',
            'fallback_used': False,
            'guardrail_actions': [],
        }
        tools = self.tool_registry.list_tools()
        recent_messages = [{'role': item.role, 'content': item.content} for item in state.messages[-6:]]

        try:
            planner_outcome = self.planner.plan(
                user_input=user_input,
                system_prompt=system_prompt,
                state_summary=state.context.get('conversation_summary', ''),
                recent_messages=recent_messages,
            )
            planner_debug['raw_planner_output'] = planner_outcome.raw_response[:1500]
            planner_debug['parsed_planner_payload'] = planner_outcome.parsed_payload
            decision = planner_outcome.decision
        except (PlannerUnavailableError, PlannerOutputError) as exc:
            decision = self.fallback_model.decide(user_input, state, tools, system_prompt)
            planner_debug['planner_source'] = 'heuristic_fallback'
            planner_debug['fallback_used'] = True
            planner_debug['fallback_reason'] = str(exc)
            planner_debug['rationale'] = decision.rationale
            planner_debug['selected_task_type'] = decision.metadata.get('task_type')
            planner_debug['selected_response_mode'] = decision.metadata.get('response_mode')
            planner_debug['tool_calls'] = [self._tool_call_payload(call) for call in decision.tool_calls]
            planner_debug['mode'] = decision.mode
            return decision, planner_debug

        guardrail_result = self.guardrails.validate(
            decision=decision,
            user_input=user_input,
            state=state,
            tools=tools,
            system_prompt=system_prompt,
        )
        planner_debug['guardrail_actions'] = list(guardrail_result.actions)
        planner_debug['fallback_used'] = guardrail_result.fallback_used
        if guardrail_result.fallback_reason:
            planner_debug['fallback_reason'] = guardrail_result.fallback_reason
        decision = guardrail_result.decision
        planner_debug['rationale'] = decision.rationale
        planner_debug['selected_task_type'] = decision.metadata.get('task_type')
        planner_debug['selected_response_mode'] = decision.metadata.get('response_mode')
        planner_debug['tool_calls'] = [self._tool_call_payload(call) for call in decision.tool_calls]
        planner_debug['mode'] = decision.mode
        return decision, planner_debug

    def _describe_tools(self, tools: Iterable[BaseTool]) -> list[str]:
        sections = []
        usage_hints = {
            'answer_ue_docs': 'Use for direct Unreal Engine knowledge questions.',
            'search_ue_docs': 'Use for workflow grounding before structured chat or file delivery.',
            'ask_clarification': 'Use when scope, audience, or constraints are missing.',
            'write_file': 'Use only when the user explicitly wants a formal file deliverable.',
            'present_file': 'Use after write_file to expose a generated artifact.',
            'task': 'Use for serial decomposition when a request clearly needs subtask execution.',
        }
        for tool in tools:
            args = ', '.join(f"{name}: {desc}" for name, desc in tool.input_schema.items()) or 'no args'
            hint = usage_hints.get(tool.name, tool.description)
            sections.append(f"- {tool.name}: {tool.description} | When to use: {hint} | Args: {args}")
        return sections

    def _describe_workflows(self) -> list[str]:
        sections = []
        for spec in list_workflow_specs():
            sections.append(
                f"- {spec.task_type}: default_response_mode={spec.default_response_mode}; clarification='{spec.clarification_question}'; plan={'; '.join(spec.default_plan)}"
            )
        return sections

    def _tool_call_payload(self, call: ToolCall) -> dict[str, object]:
        return {'name': call.name, 'args': call.args}

    def _apply_decision_state(self, state: AgentState, decision: ModelDecision) -> None:
        task_type = decision.metadata.get('task_type')
        state.set_response_mode(decision.metadata.get('response_mode'))
        if task_type and task_type != 'general_request':
            state.set_task(task_type, decision.metadata.get('plan'))
            if decision.metadata.get('compose_document'):
                state.set_deliverable({
                    'task_type': task_type,
                    'template_name': decision.metadata.get('template_name'),
                    'filename_prefix': decision.metadata.get('filename_prefix'),
                })
            else:
                state.set_deliverable(None)
        else:
            state.set_task(None, [])
            state.set_deliverable(None)
            state.set_retrieved_sources([])

    def _execute_decision(self, decision: ModelDecision, state: AgentState, user_input: str) -> AgentResponse:
        if decision.mode == 'answer':
            return AgentResponse(status='completed', output_text=decision.response_text or '')
        if decision.mode == 'tasks':
            task_tool = self.tool_registry.get_tool('task')
            task_result = self.middleware_manager.invoke_tool(
                tool=task_tool,
                state=state,
                args={'subtasks': decision.subtasks, 'original_request': user_input},
            )
            return self._build_response_from_results([task_result], state, user_input)

        tool_results: list[ToolResult] = []
        workflow_task_type = decision.metadata.get('task_type')
        for tool_call in decision.tool_calls:
            tool = self.tool_registry.get_tool(tool_call.name)
            args = dict(tool_call.args)
            if tool_call.name == 'search_ue_docs':
                if workflow_task_type == 'tutorial_writing':
                    args['query'] = user_input
                elif not args.get('query'):
                    args['query'] = user_input
                args.setdefault('top_k', 5)
            tool_results.append(self.middleware_manager.invoke_tool(tool=tool, state=state, args=args))

        spec = get_workflow_spec(decision.metadata.get('task_type', ''))
        if spec is not None:
            if decision.metadata.get('compose_document'):
                tool_results.extend(self._build_deliverable_output(spec=spec, state=state, user_input=user_input, tool_results=tool_results))
                return self._build_response_from_results(tool_results, state, user_input)
            return self._build_chat_response(spec=spec, decision=decision, state=state, user_input=user_input, tool_results=tool_results)

        return self._build_response_from_results(tool_results, state, user_input)

    def _refine_tutorial_grounding(self, *, user_input: str, state: AgentState, tool_results: list[ToolResult]):
        findings, grounding_note = self._resolve_workflow_grounding(tool_results)
        assessment = assess_tutorial_grounding(user_input, findings)
        if assessment.digest.task_focus != 'blueprint_basics' and not assessment.digest.task_specific_concepts:
            retry_query = build_tutorial_retry_query(user_input, assessment.digest.task_focus, assessment.digest.language)
            retry_result = self.middleware_manager.invoke_tool(
                tool=self.tool_registry.get_tool('search_ue_docs'),
                state=state,
                args={'query': retry_query, 'top_k': 6},
            )
            tool_results.append(retry_result)
            retry_findings, retry_note = self._resolve_workflow_grounding([retry_result])
            merged = list(findings)
            seen = {item.get('path') or item.get('title') for item in merged}
            for item in retry_findings:
                key = item.get('path') or item.get('title')
                if key not in seen:
                    seen.add(key)
                    merged.append(item)
            findings = merged
            grounding_note = grounding_note or retry_note
            assessment = assess_tutorial_grounding(user_input, findings)
        return assessment, tool_results

    def _build_deliverable_output(self, *, spec: WorkflowSpec, state: AgentState, user_input: str, tool_results: list[ToolResult]) -> list[ToolResult]:
        findings, grounding_note = self._resolve_workflow_grounding(tool_results)
        template = read_template(spec.template_name)

        if spec.task_type == 'tutorial_writing':
            assessment, tool_results = self._refine_tutorial_grounding(user_input=user_input, state=state, tool_results=tool_results)
            state.set_retrieved_sources(assessment.accepted_findings[:5])
            state.context['tutorial_debug'] = {
                'quality_status': assessment.quality_status,
                'grounding_note': assessment.grounding_note,
                'accepted_titles': [item.get('title') for item in assessment.accepted_findings[:5]],
                'rejected_titles': [item.get('title') for item in assessment.rejected_findings[:5]],
            }
            sections = get_tutorial_authoring_service().build_deliverable_sections(user_input=user_input, assessment=assessment)
            labels = {
                'label_title': '教程' if assessment.language == 'zh' else 'Tutorial',
                'label_audience': '适用对象' if assessment.language == 'zh' else 'Audience',
                'label_prerequisites': '前置准备' if assessment.language == 'zh' else 'Prerequisites',
                'label_goal': '学习目标' if assessment.language == 'zh' else 'Goal',
                'label_steps': '步骤讲解' if assessment.language == 'zh' else 'Step-by-Step Guide',
                'label_example': '练习与验证' if assessment.language == 'zh' else 'Example',
                'label_faq': '常见问题与排查' if assessment.language == 'zh' else 'Common Questions and Pitfalls',
                'label_grounding': '依据与教学补全说明' if assessment.language == 'zh' else 'Grounding and Teaching Notes',
                'label_sources': '参考资料' if assessment.language == 'zh' else 'Reference Materials',
            }
            content = template.format(
                title=user_input,
                audience=sections.audience,
                prerequisites=sections.prerequisites,
                goal=sections.goal,
                steps=sections.steps,
                example=sections.example,
                faq=sections.faq,
                grounding_and_supplementation=sections.grounding_and_supplementation,
                sources=sections.sources,
                **labels,
            )
        else:
            state.set_retrieved_sources(findings[:5])
            content = template.format(
                **build_template_payload(
                    spec=spec,
                    user_input=user_input,
                    findings=findings,
                    grounding_note=grounding_note,
                )
            )

        filename = self._suggest_filename(filename_prefix=spec.filename_prefix, user_input=user_input)
        write_result = self.middleware_manager.invoke_tool(
            tool=self.tool_registry.get_tool('write_file'),
            state=state,
            args={'path': filename, 'content': content},
        )
        if write_result.success and write_result.artifacts:
            artifact = write_result.artifacts[0]
            state.set_deliverable({'task_type': spec.task_type, 'path': artifact['path'], 'kind': artifact['kind'], 'template_name': spec.template_name})
        present_result = self.middleware_manager.invoke_tool(tool=self.tool_registry.get_tool('present_file'), state=state, args={'path': filename})
        return [write_result, present_result]

    def _build_chat_response(self, *, spec: WorkflowSpec, decision: ModelDecision, state: AgentState, user_input: str, tool_results: list[ToolResult]) -> AgentResponse:
        findings, grounding_note = self._resolve_workflow_grounding(tool_results)
        response_mode = decision.metadata.get('response_mode', spec.default_response_mode)

        if spec.task_type == 'tutorial_writing':
            assessment, tool_results = self._refine_tutorial_grounding(user_input=user_input, state=state, tool_results=tool_results)
            state.set_retrieved_sources(assessment.accepted_findings[:5])
            state.context['tutorial_debug'] = {
                'quality_status': assessment.quality_status,
                'grounding_note': assessment.grounding_note,
                'accepted_titles': [item.get('title') for item in assessment.accepted_findings[:5]],
                'rejected_titles': [item.get('title') for item in assessment.rejected_findings[:5]],
            }
            service = get_tutorial_authoring_service()
            if response_mode == 'direct_answer':
                output_text = service.build_direct_answer(user_input=user_input, assessment=assessment)
            else:
                output_text = service.build_structured_chat(user_input=user_input, assessment=assessment)
            return AgentResponse(
                status='completed',
                output_text=output_text,
                tool_outputs=[f"{r.tool_name}: {r.content or r.error}" for r in tool_results],
                artifacts=[],
            )

        state.set_retrieved_sources(findings[:5])
        if findings:
            if response_mode == 'direct_answer':
                output_text = render_direct_answer(spec=spec, user_input=user_input, findings=findings, grounding_note=grounding_note)
            else:
                output_text = render_structured_chat(spec=spec, user_input=user_input, findings=findings, grounding_note=grounding_note)
        else:
            output_text = render_chat_without_grounding(
                spec=spec,
                user_input=user_input,
                response_mode=response_mode,
                grounding_note=grounding_note or 'No validated documentation could be attached to this response.',
            )
        return AgentResponse(
            status='completed',
            output_text=output_text,
            tool_outputs=[f"{r.tool_name}: {r.content or r.error}" for r in tool_results],
            artifacts=[],
        )

    def _resolve_workflow_grounding(self, tool_results: list[ToolResult]) -> tuple[list[dict], str | None]:
        search_result = next((item for item in tool_results if item.tool_name == 'search_ue_docs'), None)
        if search_result is None:
            return [], 'Knowledge retrieval did not run for this workflow request.'
        if search_result.success:
            findings = search_result.metadata.get('results', [])
            if findings:
                return findings, None
            return [], 'The local documentation search completed but returned no matching results.'
        return [], search_result.error or 'The local documentation search is currently unavailable.'

    def _suggest_filename(self, *, filename_prefix: str, user_input: str) -> str:
        slug = re.sub(r'[^\w]+', '_', user_input, flags=re.UNICODE).strip('_')
        slug = slug[:48] or 'output'
        return f"{filename_prefix}_{slug}.md"

    def _build_response_from_results(self, tool_results: list[ToolResult], state: AgentState, user_input: str) -> AgentResponse:
        output_lines, tool_outputs, artifacts = [], [], []
        for result in tool_results:
            tool_outputs.append(f"{result.tool_name}: {result.content or result.error}")
            if result.artifacts:
                artifacts.extend(result.artifacts)
                for artifact in result.artifacts:
                    state.add_artifact(artifact)
            output_lines.append(f"{result.tool_name}: {result.content}" if result.success else f"{result.tool_name} failed: {result.error}")
        if state.deliverable and state.deliverable.get('path'):
            output_lines.append(f"deliverable: {state.deliverable['path']}")
        if not output_lines:
            output_lines.append(f"No output was generated for: {user_input}")
        return AgentResponse(status='completed', output_text='\n\n'.join(output_lines), tool_outputs=tool_outputs, artifacts=artifacts)
