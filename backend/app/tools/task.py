"""Task and clarification tools."""

from __future__ import annotations

from ..runtime.executor import SerialTaskExecutor
from ..runtime.types import ToolResult
from .base import BaseTool


class TaskTool(BaseTool):
    def __init__(self, task_executor: SerialTaskExecutor) -> None:
        super().__init__(
            name="task",
            description="Run a list of serial subtasks through the lightweight task executor.",
            input_schema={
                "subtasks": "List of string subtasks",
                "original_request": "Original user request for final aggregation",
            },
        )
        self.task_executor = task_executor

    def invoke(self, state, args):
        subtasks = args.get("subtasks", [])
        if not subtasks:
            return ToolResult.fail(tool_name=self.name, error="Task executor needs at least one subtask.")
        task_report = self.task_executor.run(subtasks=subtasks, state=state, original_request=args.get("original_request", ""))
        return ToolResult.ok(tool_name=self.name, content=task_report)


class AskClarificationTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="ask_clarification",
            description="Request more information from the user before continuing.",
            input_schema={"question": "The clarification question to ask the user"},
        )

    def invoke(self, state, args):
        question = args.get("question", "请补充更多信息。")
        return ToolResult.ok(tool_name=self.name, content=question, metadata={"clarification": True})
