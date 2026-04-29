"""Mock search tool."""

from __future__ import annotations

from ..runtime.types import ToolResult
from .base import BaseTool


class SearchTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="search",
            description="Mock web-style search tool for lightweight research.",
            input_schema={"query": "Natural language search query"},
        )
        self._documents = {
            "agent runtime": "Agent runtimes coordinate prompts, tools, state, and execution control.",
            "deerflow": "DeerFlow emphasizes runtime assembly, middleware, tools, skills, memory, and sub-agents.",
            "lightweight agent runtime": "A lightweight runtime should keep orchestration and execution separated.",
        }

    def invoke(self, state, args):
        query = args.get("query", "").strip().lower()
        if not query:
            return ToolResult.fail(tool_name=self.name, error="Query cannot be empty.")

        hits = []
        for key, value in self._documents.items():
            if key in query or any(token in value.lower() for token in query.split()):
                hits.append(f"{key}: {value}")
        if not hits:
            hits.append("No strong mock search hit. Use RAG or ask for a narrower query.")
        return ToolResult.ok(tool_name=self.name, content="\n".join(hits))

