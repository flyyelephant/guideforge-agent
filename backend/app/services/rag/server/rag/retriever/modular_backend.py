"""
Adapter for using MODULAR-RAG-MCP-SERVER as SmartUEAssistant's retrieval backend.

This module intentionally keeps the SmartUEAssistant public interface stable:
`docs`, `code`, and `assets` remain the only source categories exposed upward.
Only the underlying retrieval implementation changes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .retriever import RetrievalResponse, RetrievalResult, SourceType


class ModularBackend:
    """Adapter from SmartUEAssistant source types to MODULAR collections."""

    def __init__(
        self,
        modular_repo_root: Path,
        modular_settings_path: Path,
        source_collections: dict[SourceType, str],
    ) -> None:
        self._repo_root = modular_repo_root.resolve()
        self._settings_path = modular_settings_path.resolve()
        self._source_collections = source_collections

        self._settings = None
        self._embedding_client = None
        self._hybrid_searches: dict[str, Any] = {}
        self._vector_stores: dict[str, Any] = {}
        self._init_errors: dict[SourceType, str] = {}

    @classmethod
    def from_settings(cls, settings_path: Path, smart_cfg: dict) -> "ModularBackend":
        backend_cfg = smart_cfg.get("backend", {})
        modular_cfg = backend_cfg.get("modular", {})
        config_dir = settings_path.parent

        repo_root = (config_dir / modular_cfg.get("repo_root", "../modular")).resolve()
        settings_file = (config_dir / modular_cfg.get("settings_path", "../modular/config/settings.yaml")).resolve()

        source_collections = {
            SourceType.DOCS: modular_cfg.get("docs_collection", "ue_docs"),
            SourceType.CODE: modular_cfg.get("code_collection", "cpp_source"),
            SourceType.ASSETS: modular_cfg.get("assets_collection", "project_assets"),
        }

        return cls(
            modular_repo_root=repo_root,
            modular_settings_path=settings_file,
            source_collections=source_collections,
        )

    def search(
        self,
        query: str,
        source: SourceType,
        max_results: int = 5,
    ) -> RetrievalResponse:
        collection = self._source_collections[source]

        try:
            hybrid_search = self._get_hybrid_search(collection)
            results = hybrid_search.search(
                query=query,
                top_k=max_results,
                filters=None,
                return_details=False,
            )
        except Exception as exc:
            return RetrievalResponse(
                source=source,
                query=query,
                error=f"MODULAR retrieval failed for collection '{collection}': {exc}",
            )

        normalized = [self._build_result(item, source) for item in results]
        return RetrievalResponse(results=normalized, source=source, query=query)

    def status(self) -> dict:
        result = {}
        for source, collection in self._source_collections.items():
            try:
                store = self._get_vector_store(collection)
                count = store.collection.count()
                result[source.value] = {
                    "ready": True,
                    "doc_count": int(count),
                    "error": None,
                    "collection": collection,
                }
            except Exception as exc:
                result[source.value] = {
                    "ready": False,
                    "doc_count": 0,
                    "error": str(exc),
                    "collection": collection,
                }
        return result

    def _build_result(self, item: Any, source: SourceType) -> RetrievalResult:
        metadata = getattr(item, "metadata", {}) or {}
        text = (getattr(item, "text", "") or "").strip().replace("\n", " ")
        snippet = text[:400]

        name = (
            metadata.get("title")
            or metadata.get("name")
            or metadata.get("source_path")
            or getattr(item, "chunk_id", "")
        )
        path = (
            metadata.get("source_path")
            or metadata.get("path")
            or getattr(item, "chunk_id", "")
        )

        return RetrievalResult(
            name=str(name),
            score=float(getattr(item, "score", 0.0)),
            snippet=snippet,
            source=source,
            path=str(path),
        )

    def _ensure_import_path(self) -> None:
        repo_root_str = str(self._repo_root)
        if repo_root_str in sys.path:
            sys.path.remove(repo_root_str)
        # Put the vendored MODULAR repo ahead of `server/src`; otherwise MCP
        # imports can accidentally bind `src.*` to the wrong package tree.
        sys.path.insert(0, repo_root_str)
        self._purge_conflicting_src_modules()

    def _purge_conflicting_src_modules(self) -> None:
        """Ensure vendored modular `src.*` imports do not resolve to `server/src`."""
        src_module = sys.modules.get("src")
        if src_module is None:
            return

        module_file = getattr(src_module, "__file__", None)
        module_path = Path(module_file).resolve() if module_file else None
        if module_path is not None and self._repo_root in module_path.parents:
            return

        for module_name in list(sys.modules.keys()):
            if module_name == "src" or module_name.startswith("src."):
                del sys.modules[module_name]

    def _load_settings(self):
        self._ensure_import_path()
        from src.core.settings import load_settings

        if self._settings is None:
            self._settings = load_settings(self._settings_path)
        return self._settings

    def _get_vector_store(self, collection: str):
        if collection in self._vector_stores:
            return self._vector_stores[collection]

        self._ensure_import_path()
        import src.libs.vector_store  # noqa: F401
        from src.libs.vector_store.vector_store_factory import VectorStoreFactory

        settings = self._load_settings()
        store = VectorStoreFactory.create(settings, collection_name=collection)
        self._vector_stores[collection] = store
        return store

    def _get_embedding_client(self):
        if self._embedding_client is not None:
            return self._embedding_client

        self._ensure_import_path()
        import src.libs.embedding  # noqa: F401
        from src.libs.embedding.embedding_factory import EmbeddingFactory

        settings = self._load_settings()
        self._embedding_client = EmbeddingFactory.create(settings)
        return self._embedding_client

    def _get_hybrid_search(self, collection: str):
        if collection in self._hybrid_searches:
            return self._hybrid_searches[collection]

        self._ensure_import_path()
        from src.core.query_engine.dense_retriever import create_dense_retriever
        from src.core.query_engine.hybrid_search import create_hybrid_search
        from src.core.query_engine.query_processor import QueryProcessor
        from src.core.query_engine.sparse_retriever import create_sparse_retriever
        from src.ingestion.storage.bm25_indexer import BM25Indexer

        settings = self._load_settings()
        vector_store = self._get_vector_store(collection)
        embedding_client = self._get_embedding_client()

        dense_retriever = create_dense_retriever(
            settings=settings,
            embedding_client=embedding_client,
            vector_store=vector_store,
        )

        bm25_indexer = BM25Indexer(index_dir=str(self._repo_root / "data" / "db" / "bm25" / collection))
        sparse_retriever = create_sparse_retriever(
            settings=settings,
            bm25_indexer=bm25_indexer,
            vector_store=vector_store,
        )
        sparse_retriever.default_collection = collection

        hybrid = create_hybrid_search(
            settings=settings,
            query_processor=QueryProcessor(),
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
        )
        self._hybrid_searches[collection] = hybrid
        return hybrid
