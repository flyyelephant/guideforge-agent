"""Query rewrite layer for English-heavy UE documentation retrieval.

The runtime still accepts user queries as-is. This module adds a light bridge
between Chinese product language and the current English documentation corpus.
It prefers a deterministic terminology map and can optionally try an LLM-based
rewrite later, but rewrite is never a single point of failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .terminology import contains_cjk, expand_terms


@dataclass(frozen=True)
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    expanded_terms: list[str] = field(default_factory=list)
    bilingual_queries: list[str] = field(default_factory=list)
    strategy: str = "original_only"
    llm_used: bool = False
    llm_error: str | None = None

    def metadata(self) -> dict[str, Any]:
        payload = {
            "original_query": self.original_query,
            "rewritten_query": self.rewritten_query,
            "expanded_terms": list(self.expanded_terms),
            "bilingual_queries": list(self.bilingual_queries),
            "rewrite_strategy": self.strategy,
            "llm_used": self.llm_used,
        }
        if self.llm_error:
            payload["llm_error"] = self.llm_error
        return payload


class QueryRewriteService:
    """Small rewrite service tuned for current UE docs retrieval.

    We keep this intentionally lightweight: terminology mapping does most of the
    work, and rewrite failure simply falls back to the original query.
    """

    def rewrite(self, query: str) -> QueryRewriteResult:
        query = (query or "").strip()
        if not query:
            return QueryRewriteResult(original_query="", rewritten_query="")

        expanded_terms = expand_terms(query)
        if not contains_cjk(query):
            bilingual = [query]
            if expanded_terms:
                bilingual.append(" ".join([query, *expanded_terms]))
            rewritten = bilingual[-1]
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                expanded_terms=expanded_terms,
                bilingual_queries=bilingual,
                strategy="english_with_term_expansion" if expanded_terms else "original_only",
            )

        if expanded_terms:
            rewritten = " ".join(dict.fromkeys(expanded_terms))
            bilingual = [query, rewritten]
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                expanded_terms=expanded_terms,
                bilingual_queries=bilingual,
                strategy="dictionary_bridge",
            )

        return QueryRewriteResult(
            original_query=query,
            rewritten_query=query,
            expanded_terms=[],
            bilingual_queries=[query],
            strategy="fallback_original",
        )
