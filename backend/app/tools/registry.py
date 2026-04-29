"""Central tool registration."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from ..runtime.artifacts import ArtifactManager
from ..runtime.executor import SerialTaskExecutor
from .base import BaseTool
from .file_ops import PresentFileTool, ReadFileTool, WriteFileTool
from .rag import RagTool
from .search import SearchTool
from .task import AskClarificationTool, TaskTool
from .ue_rag import AnswerUEDocsTool, SearchUEDocsTool


class ToolRegistry:
    """A single place to register and fetch tools."""

    def __init__(self) -> None:
        self._tools: "OrderedDict[str, BaseTool]" = OrderedDict()

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool '{name}' is not registered.") from exc

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())



def get_available_tools(
    *,
    artifact_manager: ArtifactManager,
    task_executor: SerialTaskExecutor,
    enabled_tools: Iterable[str] | None,
) -> list[BaseTool]:
    tools = [
        SearchUEDocsTool(),
        AnswerUEDocsTool(),
        SearchTool(),
        RagTool(),
        ReadFileTool(),
        WriteFileTool(artifact_manager=artifact_manager),
        PresentFileTool(),
        TaskTool(task_executor=task_executor),
        AskClarificationTool(),
    ]

    if enabled_tools is None:
        return tools

    allowed = set(enabled_tools)
    return [tool for tool in tools if tool.name in allowed]
