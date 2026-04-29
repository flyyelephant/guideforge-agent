"""Generate grounded answers on top of the docs retriever.

This module stays on the SmartUEAssistant side of the integration boundary:
- retrieval still goes through ``rag.service`` / ``Retriever``
- generation reuses the vendored MODULAR LLM client and settings
"""

from __future__ import annotations

import sys
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from rag.retriever import RetrievalResponse


@dataclass
class AnswerSource:
    """Normalized source entry attached to a generated answer."""

    name: str
    path: str
    score: float


@dataclass
class RAGAnswerResponse:
    """Final answer payload returned by the answer layer."""

    answer: str
    sources: list[AnswerSource] = field(default_factory=list)
    error: Optional[str] = None

    def ok(self) -> bool:
        return self.error is None


class DocsAnswerService:
    """Turn retrieved UE docs chunks into a final grounded answer."""

    def __init__(self, smart_settings_path: Path) -> None:
        self._smart_settings_path = smart_settings_path.resolve()
        self._smart_settings = yaml.safe_load(self._smart_settings_path.read_text(encoding="utf-8")) or {}
        self._modular_root, self._modular_settings_path = self._resolve_modular_paths()
        self._modular_settings = None
        self._llm = None

    def answer(
        self,
        query: str,
        retrieval: RetrievalResponse,
        history: Optional[list[dict]] = None,
        scene_context: str = "",
    ) -> RAGAnswerResponse:
        """Generate an answer strictly grounded in retrieved docs."""
        if not retrieval.ok():
            return RAGAnswerResponse(
                answer="当前文档检索失败，暂时无法生成基于知识库的回答。",
                error=retrieval.error,
            )

        if retrieval.empty():
            return RAGAnswerResponse(
                answer="我没有在当前 UE 文档知识库里找到足够相关的内容，暂时不能给出可靠结论。",
                sources=[],
            )

        sources = self._build_sources(retrieval)
        if not self._has_grounded_match(query, retrieval):
            return RAGAnswerResponse(
                answer="当前检索结果里没有足够直接、可靠的文档片段能回答这个问题。请换更具体的关键词，或补充相关 UE 术语后再试。",
                sources=sources,
            )

        try:
            llm = self._get_llm()
            messages = self._build_messages(
                query=query,
                retrieval=retrieval,
                history=history or [],
                scene_context=scene_context,
            )
            response = llm.chat(messages)
            return RAGAnswerResponse(
                answer=self._normalize_answer(response.content),
                sources=sources,
            )
        except Exception as exc:
            # Keep a deterministic fallback so the chat endpoint remains usable
            # even if the generation provider is temporarily unavailable.
            return RAGAnswerResponse(
                answer=self._build_fallback_answer(query, retrieval),
                sources=sources,
                error=str(exc),
            )

    def _resolve_modular_paths(self) -> tuple[Path, Path]:
        backend_cfg = self._smart_settings.get("backend", {}).get("modular", {})
        config_dir = self._smart_settings_path.parent
        modular_root = (config_dir / backend_cfg.get("repo_root", "../modular")).resolve()
        modular_settings = (config_dir / backend_cfg.get("settings_path", "../modular/config/settings.yaml")).resolve()
        return modular_root, modular_settings

    def _ensure_modular_import_path(self) -> None:
        modular_root_str = str(self._modular_root)
        if modular_root_str in sys.path:
            sys.path.remove(modular_root_str)
        sys.path.insert(0, modular_root_str)
        self._purge_conflicting_src_modules()

    def _purge_conflicting_src_modules(self) -> None:
        """Force vendored MODULAR imports to win over ``server/src``."""
        src_module = sys.modules.get("src")
        if src_module is None:
            return

        module_file = getattr(src_module, "__file__", None)
        module_path = Path(module_file).resolve() if module_file else None
        if module_path is not None and self._modular_root in module_path.parents:
            return

        for module_name in list(sys.modules.keys()):
            if module_name == "src" or module_name.startswith("src."):
                del sys.modules[module_name]

    def _load_modular_settings(self):
        if self._modular_settings is not None:
            return self._modular_settings

        self._ensure_modular_import_path()
        from src.core.settings import load_settings

        self._modular_settings = load_settings(self._modular_settings_path)
        return self._modular_settings

    def _get_llm(self):
        if self._llm is not None:
            return self._llm

        self._ensure_modular_import_path()
        from src.libs.llm.base_llm import Message
        from src.libs.llm.llm_factory import LLMFactory

        self._message_cls = Message
        self._llm = LLMFactory.create(self._load_modular_settings())
        return self._llm

    def _build_messages(
        self,
        query: str,
        retrieval: RetrievalResponse,
        history: list[dict],
        scene_context: str,
    ):
        self._get_llm()

        max_history = 6
        context_blocks = []
        for index, result in enumerate(retrieval.results, start=1):
            context_blocks.append(
                "\n".join(
                    [
                        f"[Retrieved {index}]",
                        f"Title: {result.name}",
                        f"Path: {result.path}",
                        f"Score: {result.score}",
                        f"Content: {result.snippet}",
                    ]
                )
            )

        system_prompt = (
            "你是 SmartUEAssistant 的 UE 文档客服回答模块。"
            "你只能根据提供的检索片段回答，不要编造未在上下文中出现的 UE 事实。"
            "不要补充你自己的常识、不要引用外部链接、不要假设文档之外的 Unreal 结论。"
            "如果上下文不足，就明确说不知道或信息不足。"
            "回答使用中文，简洁、直接、面向实际操作。"
            "输出纯文本，不要使用 Markdown 粗体、星号列表或代码围栏。"
            "如果给出结论，优先说明依据来自哪些检索片段。"
        )
        if scene_context:
            system_prompt += f"\n\n附加场景信息：\n{scene_context}"

        user_prompt = (
            f"用户问题：{query}\n\n"
            f"可用文档片段：\n{'\n\n'.join(context_blocks)}\n\n"
            "请基于这些文档片段回答。"
        )

        messages = [self._message_cls(role="system", content=system_prompt)]
        for item in history[-max_history:]:
            role = item.get("role", "")
            content = item.get("content", "")
            if role in {"user", "assistant"} and content:
                messages.append(self._message_cls(role=role, content=content))
        messages.append(self._message_cls(role="user", content=user_prompt))
        return messages

    def _build_sources(self, retrieval: RetrievalResponse) -> list[AnswerSource]:
        sources: list[AnswerSource] = []
        seen_paths: set[str] = set()
        for result in retrieval.results:
            path = str(result.path or "").strip()
            dedupe_key = path or result.name
            if dedupe_key in seen_paths:
                continue
            seen_paths.add(dedupe_key)
            sources.append(AnswerSource(name=result.name, path=path, score=result.score))
            if len(sources) >= 3:
                break
        return sources

    def _has_grounded_match(self, query: str, retrieval: RetrievalResponse) -> bool:
        query_terms = self._extract_query_terms(query)
        if not query_terms:
            return True

        for result in retrieval.results:
            haystack = " ".join([result.name, result.path, result.snippet]).lower()
            if any(term in haystack for term in query_terms):
                return True
        return False

    def _extract_query_terms(self, query: str) -> list[str]:
        ascii_terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_]+", query) if len(term) >= 3]
        cjk_terms = [term for term in re.findall(r"[\u4e00-\u9fff]{2,}", query) if len(term) >= 2]
        return ascii_terms + cjk_terms

    def _normalize_answer(self, answer: str) -> str:
        normalized = answer.replace("**", "").replace("*", "")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _build_fallback_answer(self, query: str, retrieval: RetrievalResponse) -> str:
        best = retrieval.results[0]
        answer = (
            f"关于“{query}”，我先给出基于检索结果的保守结论：\n"
            f"{best.snippet}"
        )
        return self._normalize_answer(answer)
