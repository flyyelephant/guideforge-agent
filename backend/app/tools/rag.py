"""Mock RAG tool."""

from __future__ import annotations

from ..runtime.types import ToolResult
from .base import BaseTool


class RagTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="rag",
            description="Mock knowledge-base lookup tool.",
            input_schema={"query": "Question or concept to retrieve from the local knowledge base"},
        )
        self._knowledge = {
            "rag": "RAG combines retrieval with generation so the model answers with retrieved context.",
            "tool": "A tool is an executable runtime capability, not just a prompt hint.",
            "prompt": "Prompts define method and behavior constraints; they do not execute side effects.",
            "deerflow": "DeerFlow separates orchestration, tools, middleware, skills, memory, and execution boundaries.",
        }

    def invoke(self, state, args):
        query = args.get("query", "").strip().lower()
        if not query:
            return ToolResult.fail(tool_name=self.name, error="Query cannot be empty.")

        matches = []
        for key, value in self._knowledge.items():
            if key in query:
                matches.append(f"{key}: {value}")
        if not matches:
            matches.append("No exact knowledge hit. The local KB is intentionally small in v1.")
        return ToolResult.ok(tool_name=self.name, content="\n".join(matches))

