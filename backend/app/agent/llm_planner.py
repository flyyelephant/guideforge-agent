"""LLM-driven lead planner.

This planner upgrades the runtime from a purely heuristic router into a true
lead-agent shape: the model proposes a structured decision, while runtime
validation and execution stay outside the model.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..runtime.types import ModelDecision, ToolCall


@dataclass
class PlannerOutcome:
    decision: ModelDecision
    raw_response: str
    parsed_payload: dict[str, Any]


class PlannerUnavailableError(RuntimeError):
    pass


class PlannerOutputError(RuntimeError):
    pass


class LLMPlanner:
    """Generate a structured planning decision with the configured LLM."""

    def __init__(self, smart_settings_path: Path | None = None) -> None:
        if smart_settings_path is None:
            smart_settings_path = (
                Path(__file__).resolve().parent.parent
                / 'services'
                / 'rag'
                / 'server'
                / 'rag'
                / 'config'
                / 'settings.yaml'
            )
        self._smart_settings_path = smart_settings_path.resolve()
        self._smart_settings = yaml.safe_load(self._smart_settings_path.read_text(encoding='utf-8')) or {}
        self._modular_root, self._modular_settings_path = self._resolve_modular_paths()
        self._modular_settings = None
        self._llm = None
        self._message_cls = None

    def plan(
        self,
        *,
        user_input: str,
        system_prompt: str,
        state_summary: str,
        recent_messages: list[dict[str, str]],
    ) -> PlannerOutcome:
        try:
            llm = self._get_llm()
            messages = self._build_messages(
                system_prompt=system_prompt,
                user_input=user_input,
                state_summary=state_summary,
                recent_messages=recent_messages,
            )
            response = llm.chat(messages)
        except Exception as exc:
            raise PlannerUnavailableError(str(exc)) from exc

        raw = (getattr(response, 'content', '') or '').strip()
        if not raw:
            raise PlannerOutputError('Planner returned empty content.')

        payload = self._parse_payload(raw)
        decision = self._to_decision(payload)
        return PlannerOutcome(decision=decision, raw_response=raw, parsed_payload=payload)

    def _resolve_modular_paths(self) -> tuple[Path, Path]:
        backend_cfg = self._smart_settings.get('backend', {}).get('modular', {})
        config_dir = self._smart_settings_path.parent
        modular_root = (config_dir / backend_cfg.get('repo_root', '../modular')).resolve()
        modular_settings = (config_dir / backend_cfg.get('settings_path', '../modular/config/settings.yaml')).resolve()
        return modular_root, modular_settings

    def _ensure_modular_import_path(self) -> None:
        modular_root_str = str(self._modular_root)
        if modular_root_str in sys.path:
            sys.path.remove(modular_root_str)
        sys.path.insert(0, modular_root_str)
        self._purge_conflicting_src_modules()

    def _purge_conflicting_src_modules(self) -> None:
        src_module = sys.modules.get('src')
        if src_module is None:
            return

        module_file = getattr(src_module, '__file__', None)
        module_path = Path(module_file).resolve() if module_file else None
        if module_path is not None and self._modular_root in module_path.parents:
            return

        for module_name in list(sys.modules.keys()):
            if module_name == 'src' or module_name.startswith('src.'):
                del sys.modules[module_name]

    def _load_modular_settings(self):
        if self._modular_settings is not None:
            return self._modular_settings

        self._ensure_modular_import_path()
        from src.core.settings import load_settings

        self._modular_settings = load_settings(self._modular_settings_path)
        return self._modular_settings

    def _get_llm(self):
        if self._llm is not None and self._message_cls is not None:
            return self._llm

        self._ensure_modular_import_path()
        from src.libs.llm.base_llm import Message
        from src.libs.llm.llm_factory import LLMFactory

        self._message_cls = Message
        self._llm = LLMFactory.create(self._load_modular_settings())
        return self._llm

    def _build_messages(
        self,
        *,
        system_prompt: str,
        user_input: str,
        state_summary: str,
        recent_messages: list[dict[str, str]],
    ):
        self._get_llm()
        history_lines = []
        for item in recent_messages[-4:]:
            role = item.get('role', 'user')
            content = (item.get('content', '') or '').strip()
            if not content:
                continue
            history_lines.append(f"{role}: {content}")
        history_block = '\n'.join(history_lines) if history_lines else 'No recent conversation history.'
        user_prompt = (
            'Return exactly one JSON object that matches the planning contract.\n\n'
            f'Current user request:\n{user_input}\n\n'
            f'State summary:\n{state_summary or "No running summary yet."}\n\n'
            f'Recent conversation:\n{history_block}\n\n'
            'Do not add markdown fences or commentary. Return JSON only.'
        )
        return [
            self._message_cls(role='system', content=system_prompt),
            self._message_cls(role='user', content=user_prompt),
        ]

    def _parse_payload(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if not match:
                raise PlannerOutputError('Planner output was not valid JSON.')
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise PlannerOutputError(f'Planner JSON parse failed: {exc}') from exc

        if not isinstance(payload, dict):
            raise PlannerOutputError('Planner output must be a JSON object.')
        return payload

    def _to_decision(self, payload: dict[str, Any]) -> ModelDecision:
        mode = str(payload.get('mode', 'answer')).strip()
        response_text = payload.get('response_text')
        if response_text is not None:
            response_text = str(response_text)

        tool_calls: list[ToolCall] = []
        for item in payload.get('tool_calls', []) or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name', '')).strip()
            args = item.get('args', {})
            if not isinstance(args, dict):
                args = {}
            if name:
                tool_calls.append(ToolCall(name=name, args=args))

        subtasks = [str(item).strip() for item in payload.get('subtasks', []) or [] if str(item).strip()]
        metadata = payload.get('metadata', {})
        if not isinstance(metadata, dict):
            metadata = {}
        if 'task_type' in payload:
            metadata['task_type'] = payload.get('task_type')
        if 'response_mode' in payload:
            metadata['response_mode'] = payload.get('response_mode')
        if 'needs_clarification' in payload:
            metadata['needs_clarification'] = bool(payload.get('needs_clarification'))

        return ModelDecision(
            mode=mode,
            response_text=response_text,
            tool_calls=tool_calls,
            subtasks=subtasks,
            rationale=str(payload.get('rationale', '') or ''),
            metadata=metadata,
        )
