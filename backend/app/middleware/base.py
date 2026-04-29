"""Minimal middleware interfaces and orchestration."""

from __future__ import annotations

from typing import Callable

from ..agent.state import AgentState
from ..runtime.types import AgentResponse, ModelDecision, ToolResult
from ..tools.base import BaseTool


class BaseMiddleware:
    """Lifecycle hooks are intentionally small and explicit."""

    def before_agent(self, state: AgentState, user_input: str) -> None:
        return None

    def after_model(self, state: AgentState, decision: ModelDecision) -> AgentResponse | None:
        return None

    def wrap_tool_call(
        self,
        *,
        tool: BaseTool,
        state: AgentState,
        args: dict,
        call_next: Callable[[], ToolResult],
    ) -> ToolResult:
        return call_next()

    def after_agent(self, state: AgentState, response: AgentResponse) -> AgentResponse | None:
        return None


class MiddlewareManager:
    def __init__(self, middlewares: list[BaseMiddleware]) -> None:
        self.middlewares = middlewares

    def before_agent(self, state: AgentState, user_input: str) -> None:
        for middleware in self.middlewares:
            middleware.before_agent(state, user_input)

    def after_model(self, state: AgentState, decision: ModelDecision) -> AgentResponse | None:
        for middleware in self.middlewares:
            response = middleware.after_model(state, decision)
            if response is not None:
                return response
        return None

    def invoke_tool(self, *, tool: BaseTool, state: AgentState, args: dict) -> ToolResult:
        def call_tool() -> ToolResult:
            return tool.invoke(state, args)

        call_next = call_tool
        for middleware in reversed(self.middlewares):
            current = call_next

            def wrapper(mw=middleware, nxt=current):
                return mw.wrap_tool_call(tool=tool, state=state, args=args, call_next=nxt)

            call_next = wrapper
        return call_next()

    def after_agent(self, state: AgentState, response: AgentResponse) -> AgentResponse | None:
        current = response
        for middleware in self.middlewares:
            maybe = middleware.after_agent(state, current)
            if maybe is not None:
                current = maybe
        return current

