"""Convert tool exceptions into stable tool results."""

from __future__ import annotations

from .base import BaseMiddleware
from ..runtime.types import ToolResult


class ToolErrorMiddleware(BaseMiddleware):
    def wrap_tool_call(self, *, tool, state, args, call_next):
        try:
            return call_next()
        except Exception as exc:  # pragma: no cover - intentionally broad in middleware
            return ToolResult.fail(tool_name=tool.name, error=str(exc))

