"""Runtime-facing knowledge retrieval adapter.

The public tool names stay UE-oriented for compatibility with the current
workflow chain, but the internal implementation is intentionally phrased as a
lightweight knowledge provider so future local sources can be added without
rewriting the runtime contract.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .query_rewrite import QueryRewriteResult, QueryRewriteService

SERVER_ROOT = Path(__file__).resolve().parent / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from rag.answer_service import DocsAnswerService
from rag.retriever.retriever import RetrievalResponse, RetrievalResult, SourceType, _SimpleBackend


@dataclass(frozen=True)
class KnowledgeSourceDescriptor:
    source_id: str
    label: str
    docs_path: Path


class LocalDocsKnowledgeProvider:
    """Current concrete provider backed by local documentation files."""

    def __init__(self, settings_path: Path, *, source_id: str, label: str) -> None:
        self._settings_path = settings_path.resolve()
        self._rag_root = self._settings_path.parent.parent
        self._services_root = self._rag_root.parent.parent
        docs_path = self._resolve_docs_path()
        self.descriptor = KnowledgeSourceDescriptor(
            source_id=source_id,
            label=label,
            docs_path=docs_path,
        )
        self._backend = _SimpleBackend(
            simple_rag_path=self._rag_root / "scripts" / "simple_rag_query.py",
            docs_dir=docs_path,
            code_dir=docs_path,
            assets_dir=docs_path,
        )
        self._answer_service = DocsAnswerService(self._settings_path)
        self._rewrite_service = QueryRewriteService()

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        retrieval, rewrite = self._search_with_rewrite(query=query, top_k=top_k)
        if not retrieval.ok():
            raise RuntimeError(f"Local knowledge retrieval is unavailable: {retrieval.error}")
        return self._normalize_results(retrieval, rewrite)

    def answer(self, query: str, top_k: int = 5) -> dict[str, Any]:
        retrieval, rewrite = self._search_with_rewrite(query=query, top_k=top_k)
        if not retrieval.ok():
            return {
                "answer": "I could not validate this request against the local documentation because retrieval is currently unavailable.",
                "sources": [],
                "error": retrieval.error,
                "retrieval_status": "unavailable",
                "knowledge_source": self._source_metadata(),
                "query_rewrite": rewrite.metadata(),
            }

        if retrieval.empty():
            return {
                "answer": "I could not find enough relevant local documentation to answer this reliably.",
                "sources": [],
                "retrieval_status": "empty",
                "knowledge_source": self._source_metadata(),
                "query_rewrite": rewrite.metadata(),
            }

        sources = self._normalize_sources([], retrieval, rewrite)
        try:
            response = self._answer_service.answer(query=query, retrieval=retrieval)
            sources = self._normalize_sources(getattr(response, "sources", []), retrieval, rewrite)
            answer = (getattr(response, "answer", "") or "").strip()
            error = getattr(response, "error", None)
            if error or not answer:
                answer = self._build_conservative_answer(query, retrieval)
            payload = {
                "answer": answer,
                "sources": sources,
                "retrieval_status": "grounded" if not error else "grounded_fallback",
                "knowledge_source": self._source_metadata(),
                "query_rewrite": rewrite.metadata(),
            }
            if error:
                payload["error"] = error
            return payload
        except Exception as exc:
            return {
                "answer": self._build_conservative_answer(query, retrieval),
                "sources": sources,
                "error": str(exc),
                "retrieval_status": "grounded_fallback",
                "knowledge_source": self._source_metadata(),
                "query_rewrite": rewrite.metadata(),
            }

    def search_raw(self, query: str, top_k: int = 5) -> RetrievalResponse:
        return self._backend.search(query=query, source=SourceType.DOCS, max_results=top_k)

    def _search_with_rewrite(self, query: str, top_k: int) -> tuple[RetrievalResponse, QueryRewriteResult]:
        rewrite = self._rewrite_service.rewrite(query)
        retrievals: list[tuple[str, RetrievalResponse]] = []
        seen_queries: set[str] = set()
        for candidate in rewrite.bilingual_queries or [query]:
            normalized = (candidate or "").strip()
            if not normalized or normalized in seen_queries:
                continue
            seen_queries.add(normalized)
            retrievals.append((normalized, self.search_raw(query=normalized, top_k=top_k)))

        if not retrievals:
            return RetrievalResponse(source=SourceType.DOCS, query=query, error="No query candidates were available for retrieval."), rewrite

        merged = self._merge_retrievals(query=query, retrievals=retrievals, rewrite=rewrite, top_k=top_k)
        return merged, rewrite

    def _merge_retrievals(
        self,
        *,
        query: str,
        retrievals: list[tuple[str, RetrievalResponse]],
        rewrite: QueryRewriteResult,
        top_k: int,
    ) -> RetrievalResponse:
        errors = [item.error for _, item in retrievals if not item.ok() and item.error]
        successful = [(candidate, item) for candidate, item in retrievals if item.ok()]
        if not successful:
            return RetrievalResponse(source=SourceType.DOCS, query=query, error="; ".join(errors) or "Local retrieval failed.")

        merged_by_path: dict[str, RetrievalResult] = {}
        for candidate, retrieval in successful:
            candidate_is_original = candidate == rewrite.original_query
            for result in retrieval.results:
                key = result.path or result.name
                adjusted_score = float(result.score)
                if candidate_is_original:
                    adjusted_score += 0.05
                elif candidate == rewrite.rewritten_query and candidate != rewrite.original_query:
                    adjusted_score += 0.15
                if key in merged_by_path and merged_by_path[key].score >= adjusted_score:
                    continue
                merged_by_path[key] = RetrievalResult(
                    name=result.name,
                    score=adjusted_score,
                    snippet=result.snippet,
                    source=result.source,
                    path=result.path,
                )

        merged_results = sorted(merged_by_path.values(), key=lambda item: item.score, reverse=True)[:top_k]
        return RetrievalResponse(results=merged_results, source=SourceType.DOCS, query=query)

    def _resolve_docs_path(self) -> Path:
        candidates = [
            self._services_root / "knowledge" / "ue_docs" / "raw",
            self._services_root / "knowledge" / "ue_docs" / "raw" / "markdown",
            self._services_root / "knowledge" / "ue_docs" / "raw" / "udn",
            self._services_root / "knowledge" / "ue_docs" / "converted",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return candidates[0].resolve()

    def _normalize_results(self, retrieval: RetrievalResponse, rewrite: QueryRewriteResult) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in getattr(retrieval, "results", []):
            source_value = getattr(item.source, "value", str(item.source))
            results.append(
                {
                    "title": item.name,
                    "source": source_value,
                    "path": item.path,
                    "snippet": item.snippet,
                    "score": item.score,
                    "metadata": {
                        "source_type": source_value,
                        "query": retrieval.query,
                        "knowledge_source": self._source_metadata(),
                        "query_rewrite": rewrite.metadata(),
                    },
                }
            )
        return results

    def _normalize_sources(self, raw_sources: list[Any], retrieval: RetrievalResponse, rewrite: QueryRewriteResult) -> list[dict[str, Any]]:
        indexed: dict[str, RetrievalResult] = {}
        for item in getattr(retrieval, "results", []):
            indexed[item.path or item.name] = item

        if not raw_sources:
            raw_sources = getattr(retrieval, "results", [])[:3]

        normalized: list[dict[str, Any]] = []
        for item in raw_sources:
            title = getattr(item, "name", None) or getattr(item, "title", None) or "Untitled source"
            path = getattr(item, "path", "") or ""
            score = float(getattr(item, "score", 0.0) or 0.0)
            matched = indexed.get(path or title)
            snippet = matched.snippet if matched is not None else ""
            normalized.append(
                {
                    "title": title,
                    "path": path,
                    "score": score,
                    "snippet": snippet,
                    "knowledge_source": self._source_metadata(),
                    "query_rewrite": rewrite.metadata(),
                }
            )
        return normalized[:5]

    def _build_conservative_answer(self, query: str, retrieval: RetrievalResponse) -> str:
        bullets = []
        for item in getattr(retrieval, "results", [])[:3]:
            snippet = (item.snippet or "Use the cited document as the grounding source for the next step.").strip()
            bullets.append(f"- {item.name}: {snippet}")
        evidence = "\n".join(bullets) or "- No grounded excerpts were available."
        return (
            f"I could not produce a fully generated answer for `{query}`, so here is a conservative summary based on the local documentation hits.\n\n"
            f"Grounded evidence:\n{evidence}"
        )

    def _source_metadata(self) -> dict[str, str]:
        return {
            "source_id": self.descriptor.source_id,
            "label": self.descriptor.label,
            "docs_path": str(self.descriptor.docs_path),
        }


class UEDocsRAGService:
    """Compatibility wrapper kept for the current UE-oriented tools."""

    def __init__(self) -> None:
        settings_path = Path(__file__).resolve().parent / "server" / "rag" / "config" / "settings.yaml"
        self._provider = LocalDocsKnowledgeProvider(
            settings_path=settings_path,
            source_id="ue_official_local_docs",
            label="Local Unreal Engine official docs",
        )
        self._settings_path = settings_path.resolve()

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def search(self, query: str, top_k: int = 5, **kwargs: Any) -> list[dict[str, Any]]:
        return self._provider.search(query=query, top_k=top_k)

    def answer(self, query: str, top_k: int = 5, **kwargs: Any) -> dict[str, Any]:
        return self._provider.answer(query=query, top_k=top_k)


_service_singleton: UEDocsRAGService | None = None


def get_ue_docs_rag_service() -> UEDocsRAGService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = UEDocsRAGService()
    return _service_singleton
