#!/usr/bin/env python3
"""Minimal local RAG query helper.

This keeps the original SimpleRAGClient contract, but removes noisy console
output and applies a tiny amount of query-term filtering so generic workflow
phrases do not dominate local-doc retrieval.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Dict, List


class SimpleRAGClient:
    """A lightweight全文检索客户端 used as the offline fallback backend."""

    def __init__(self, docs_dir: str | None = None):
        self.docs_dir = os.path.expanduser(docs_dir or "~/Documents/unreal_rag/docs/converted/markdown")
        self.index: dict[str, dict[str, str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        if not os.path.exists(self.docs_dir):
            return

        supported_patterns = ("*.md", "*.udn", "*.txt")
        files = []
        for pattern in supported_patterns:
            files.extend(Path(self.docs_dir).rglob(pattern))
        for doc_file in files:
            try:
                content = doc_file.read_text(encoding="utf-8", errors="ignore").lower()
                self.index[str(doc_file)] = {
                    "content": content,
                    "path": str(doc_file),
                    "name": doc_file.name,
                }
            except Exception:
                continue

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        query_lower = query.lower()
        query_terms = self._prepare_query_terms(query_lower)
        results = []

        for doc_path, doc_data in self.index.items():
            content = doc_data["content"]
            name = doc_data["name"].lower()
            score = 0

            for term in query_terms:
                count = content.count(term)
                if count > 0:
                    score += count
                title_hits = name.count(term)
                if title_hits > 0:
                    score += title_hits * 5

            if score > 0:
                snippets = self._extract_snippets(content, query_terms)
                results.append(
                    {
                        "path": doc_path,
                        "name": doc_data["name"],
                        "score": score,
                        "snippets": snippets,
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    def _prepare_query_terms(self, query_lower: str) -> List[str]:
        stop_words = {
            "the", "and", "for", "with", "from", "that", "this",
            "what", "how", "give", "help", "write", "create",
            "generate", "document", "docs", "proposal", "tutorial",
            "workflow", "support", "outline", "review", "reviewing",
            "small", "team", "local", "official", "engine", "unreal",
            "editor", "ue",
        }
        ascii_terms = [
            term for term in re.findall(r"[a-z0-9_]+", query_lower)
            if len(term) >= 3 and term not in stop_words
        ]
        cjk_terms = [
            term for term in re.findall(r"[\u4e00-\u9fff]{2,}", query_lower)
            if len(term) >= 2
        ]
        terms = ascii_terms + cjk_terms
        return terms or [term for term in query_lower.split() if len(term) >= 3]

    def _extract_snippets(self, content: str, query_terms: List[str], context_chars: int = 200) -> List[str]:
        snippets = []
        lines = content.split("\n")

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(term in line_lower for term in query_terms):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                snippet = "\n".join(lines[start:end])
                snippets.append(snippet[:context_chars * 2])
                if len(snippets) >= 3:
                    break

        return snippets

    def interactive_query(self) -> None:
        print("Local UE docs query helper. Type 'quit' to exit.")
        while True:
            try:
                query = input("Query: ").strip()
                if query.lower() in {"quit", "exit", "q"}:
                    break
                if not query:
                    continue
                results = self.search(query, max_results=5)
                if not results:
                    print("No matching documents found.\n")
                    continue
                for index, result in enumerate(results, start=1):
                    print(f"{index}. {result['name']} (score={result['score']})")
                    print(f"   {result['path']}")
                    if result["snippets"]:
                        print(f"   {result['snippets'][0][:300]}...")
                    print()
            except KeyboardInterrupt:
                break


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal local UE docs query helper")
    parser.add_argument("--docs-dir", default="~/Documents/unreal_rag/docs/raw", help="Directory containing local docs (md/udn/txt)")
    parser.add_argument("--query", help="Single query. If omitted, start interactive mode")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum results")
    args = parser.parse_args()

    client = SimpleRAGClient(args.docs_dir)
    if args.query:
        results = client.search(args.query, args.max_results)
        print(f"Query: {args.query}\n")
        for index, result in enumerate(results, start=1):
            print(f"{index}. {result['name']} (score={result['score']})")
            print(f"   {result['path']}")
    else:
        client.interactive_query()


if __name__ == "__main__":
    main()
