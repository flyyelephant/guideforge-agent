"""
RAG unified retrieval layer.

This layer preserves SmartUEAssistant's existing `docs/code/assets` retrieval
interface while allowing the underlying backend to be swapped. The current
backend can be either:

- `simple`: the original keyword-based `SimpleRAGClient`
- `modular`: the external MODULAR-RAG hybrid retrieval pipeline
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class SourceType(str, Enum):
    DOCS = "docs"
    CODE = "code"
    ASSETS = "assets"


@dataclass
class RetrievalResult:
    """A normalized retrieval result returned to the MCP tool layer."""

    name: str
    score: float
    snippet: str
    source: SourceType
    path: str = ""

    def is_empty(self) -> bool:
        return not self.snippet.strip()


@dataclass
class RetrievalResponse:
    """A normalized retrieval response returned to the MCP tool layer."""

    results: list[RetrievalResult] = field(default_factory=list)
    source: SourceType = SourceType.DOCS
    query: str = ""
    error: Optional[str] = None

    def ok(self) -> bool:
        return self.error is None

    def empty(self) -> bool:
        return self.ok() and len(self.results) == 0


def _load_simple_rag(simple_rag_path: Path, docs_dir: Path):
    """Load a `SimpleRAGClient` instance from the legacy script."""
    if not simple_rag_path.exists():
        raise FileNotFoundError(f"simple_rag_query.py not found: {simple_rag_path}")
    if not docs_dir.exists():
        raise FileNotFoundError(f"indexed docs directory not found: {docs_dir}")

    spec = importlib.util.spec_from_file_location("simple_rag_query", simple_rag_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module spec from {simple_rag_path}")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Redirect noisy legacy progress logs so Windows GBK consoles do not break init.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return mod.SimpleRAGClient(docs_dir=str(docs_dir))


def _build_simple_result(raw: dict, source: SourceType) -> RetrievalResult:
    """Convert a `SimpleRAGClient` result into the normalized result shape."""
    snippets = raw.get("snippets", [])
    snippet = snippets[0].strip().replace("\n", " ")[:400] if snippets else ""
    return RetrievalResult(
        name=raw.get("name", ""),
        score=float(raw.get("score", 0)),
        snippet=snippet,
        source=source,
        path=raw.get("path", ""),
    )


class _SimpleBackend:
    """Original keyword-only backend used before MODULAR integration."""

    def __init__(
        self,
        simple_rag_path: Path,
        docs_dir: Path,
        code_dir: Path,
        assets_dir: Path,
    ) -> None:
        self._simple_rag_path = simple_rag_path
        self._dirs = {
            SourceType.DOCS: docs_dir,
            SourceType.CODE: code_dir,
            SourceType.ASSETS: assets_dir,
        }
        self._clients: dict[SourceType, object] = {}
        self._init_errors: dict[SourceType, str] = {}

    def search(
        self,
        query: str,
        source: SourceType,
        max_results: int = 5,
    ) -> RetrievalResponse:
        client, error = self._get_client(source)
        if error:
            return RetrievalResponse(source=source, query=query, error=error)

        try:
            raws = client.search(query, max_results=max_results)
            results = [_build_simple_result(item, source) for item in raws]
            return RetrievalResponse(results=results, source=source, query=query)
        except Exception as exc:
            return RetrievalResponse(
                source=source,
                query=query,
                error=f"retrieval failed: {exc}",
            )

    def status(self) -> dict:
        result = {}
        for source in SourceType:
            client, error = self._get_client(source)
            if error:
                result[source.value] = {"ready": False, "doc_count": 0, "error": error}
            else:
                result[source.value] = {
                    "ready": True,
                    "doc_count": len(getattr(client, "index", {})),
                    "error": None,
                }
        return result

    def _get_client(self, source: SourceType):
        if source in self._clients:
            return self._clients[source], None
        if source in self._init_errors:
            return None, self._init_errors[source]

        try:
            client = _load_simple_rag(self._simple_rag_path, self._dirs[source])
            self._clients[source] = client
            return client, None
        except FileNotFoundError as exc:
            error = str(exc)
            self._init_errors[source] = error
            return None, error
        except Exception as exc:
            error = f"failed to initialize {source.value} retriever: {exc}"
            self._init_errors[source] = error
            return None, error


class Retriever:
    """
    Unified retrieval facade.

    The MCP tool layer talks only to this class. Backends can be swapped by
    `server/rag/config/settings.yaml` without changing UE-side tool contracts.
    """

    def __init__(self, backend) -> None:
        self._backend = backend

    @classmethod
    def from_settings(cls, settings_path: Path) -> "Retriever":
        """Build the configured retriever backend from `settings.yaml`."""
        cfg = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
        backend_cfg = cfg.get("backend", {})
        provider = str(backend_cfg.get("provider", "simple")).strip().lower()

        if provider == "modular":
            from rag.retriever.modular_backend import ModularBackend

            backend = ModularBackend.from_settings(settings_path, cfg)
            return cls(backend)

        rag_root = settings_path.parent.parent
        mcp_root = rag_root.parent
        private_index = cfg.get("private_index", {})

        backend = _SimpleBackend(
            simple_rag_path=rag_root / "scripts" / "simple_rag_query.py",
            docs_dir=(rag_root / private_index.get("docs_output_dir", "../docs/converted/markdown")).resolve(),
            code_dir=(mcp_root / private_index.get("cpp_output_dir", "docs/converted/cpp_source")).resolve(),
            assets_dir=(mcp_root / private_index.get("assets_output_dir", "docs/converted/assets")).resolve(),
        )
        return cls(backend)

    def search(
        self,
        query: str,
        source: SourceType,
        max_results: int = 5,
    ) -> RetrievalResponse:
        return self._backend.search(query, source, min(max_results, 10))

    def status(self) -> dict:
        return self._backend.status()
