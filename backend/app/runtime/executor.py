"""Serial task executor.

This is not a recursive agent. It is a lightweight worker that can choose tools
for each subtask and return a structured report to the main agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class SerialTaskExecutor:
    def __init__(self, *, tool_registry: "ToolRegistry") -> None:
        self.tool_registry = tool_registry

    def run(self, *, subtasks: list[str], state, original_request: str) -> str:
        lines = [f"Task executor report for: {original_request or 'subtask bundle'}"]

        for index, subtask in enumerate(subtasks, start=1):
            lines.append(f"\n[{index}] {subtask}")
            result_line = self._execute_subtask(subtask, state)
            lines.append(result_line)

        return "\n".join(lines)

    def _execute_subtask(self, subtask: str, state) -> str:
        lower = subtask.lower()

        if any(keyword in subtask for keyword in ["搜索", "调研", "收集"]) or "search" in lower:
            result = self.tool_registry.get_tool("search").invoke(state, {"query": subtask})
            return f"search -> {result.content}"

        if any(keyword in subtask for keyword in ["知识", "概念", "runtime", "tool", "agent"]):
            result = self.tool_registry.get_tool("rag").invoke(state, {"query": subtask})
            return f"rag -> {result.content}"

        return "worker -> Produced a structured note without calling extra tools."
