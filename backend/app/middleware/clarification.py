"""Interrupt normal execution when the planner asks for clarification."""

from __future__ import annotations

from .base import BaseMiddleware
from ..runtime.types import AgentResponse


class ClarificationMiddleware(BaseMiddleware):
    def after_model(self, state, decision):
        if not decision.tool_calls:
            return None

        first = decision.tool_calls[0]
        if first.name != "ask_clarification":
            return None

        question = first.args.get("question", "请补充更多信息。")
        return AgentResponse(
            status="needs_clarification",
            output_text=f"我还不能安全继续执行。\n{question}",
            clarification_question=question,
        )
