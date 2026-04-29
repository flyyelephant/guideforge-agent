"""Tool wrappers around the UE docs RAG service."""

from __future__ import annotations

from ..runtime.types import ToolResult
from ..services.rag.rag_service import get_ue_docs_rag_service
from .base import BaseTool


class SearchUEDocsTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="search_ue_docs",
            description="Search Unreal Engine docs and return structured retrieval results with sources.",
            input_schema={
                "query": "The UE docs query to search for",
                "top_k": "Optional maximum number of results",
            },
        )
        self._service = get_ue_docs_rag_service()

    def invoke(self, state, args):
        query = args.get("query", "").strip()
        top_k = int(args.get("top_k", 5))
        if not query:
            return ToolResult.fail(tool_name=self.name, error="Query cannot be empty.")

        try:
            results = self._service.search(query=query, top_k=top_k)
        except Exception as exc:
            return ToolResult.fail(tool_name=self.name, error=str(exc))

        if not results:
            return ToolResult.fail(tool_name=self.name, error="No matching local UE documentation was found for this query.")

        lines = [f"Found {len(results)} local UE docs results for: {query}"]
        for index, item in enumerate(results[:top_k], start=1):
            lines.append(f"[{index}] {item['title']} (score={item['score']:.3f})")
            if item["path"]:
                lines.append(f"    {item['path']}")
            if item["snippet"]:
                lines.append(f"    {item['snippet'][:220]}")

        return ToolResult.ok(
            tool_name=self.name,
            content="\n".join(lines),
            metadata={
                "results": results,
                "query": query,
                "knowledge_source": results[0].get("metadata", {}).get("knowledge_source", {}),
            },
        )


class AnswerUEDocsTool(BaseTool):
    def __init__(self) -> None:
        super().__init__(
            name="answer_ue_docs",
            description="Answer a UE docs question using the existing grounded answer chain.",
            input_schema={
                "query": "The UE docs question to answer",
                "top_k": "Optional maximum number of retrieval hits",
            },
        )
        self._service = get_ue_docs_rag_service()

    def invoke(self, state, args):
        query = args.get("query", "").strip()
        top_k = int(args.get("top_k", 5))
        if not query:
            return ToolResult.fail(tool_name=self.name, error="Query cannot be empty.")

        try:
            payload = self._service.answer(query=query, top_k=top_k)
        except Exception as exc:
            return ToolResult.fail(tool_name=self.name, error=str(exc))

        answer = payload.get("answer", "").strip()
        error = payload.get("error")
        if not answer:
            return ToolResult.fail(tool_name=self.name, error=error or "UE docs answer service returned no answer.")

        lines = [answer]
        sources = payload.get("sources", [])
        if sources:
            lines.append("")
            lines.append("Sources:")
            for index, item in enumerate(sources, start=1):
                lines.append(f"[{index}] {item['title']}")
                if item.get("path"):
                    lines.append(f"    {item['path']}")
                if item.get("snippet"):
                    lines.append(f"    {item['snippet'][:180]}")

        return ToolResult.ok(
            tool_name=self.name,
            content="\n".join(lines),
            metadata=payload,
        )
