"""Simple context trimming."""

from __future__ import annotations

from .base import BaseMiddleware


class SummarizationMiddleware(BaseMiddleware):
    """When history grows too long, compress old messages into a cheap summary."""

    def __init__(self, *, max_messages: int = 10) -> None:
        self.max_messages = max_messages

    def before_agent(self, state, user_input):
        if len(state.messages) <= self.max_messages:
            return

        older = state.messages[:-4]
        summary_lines = [f"{message.role}: {message.content[:80]}" for message in older]
        state.context["conversation_summary"] = " | ".join(summary_lines)
        state.messages = state.messages[-4:]

