"""
RAG 服务层 —— 对外唯一接口

职责：
  - 持有 Retriever 实例（单例）
  - 处理资产检索的在线/离线降级逻辑
  - 不知道 MCP 的存在
  - rag.py（MCP 工具层）只调用这里，不直接碰 Retriever

调用方式（在 rag.py 里）：
    from rag.service import get_rag_service
    service = get_rag_service()
    response = await service.query_docs("Actor BeginPlay")
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# service.py 位于 server/rag/service.py
# retriever.py 位于 server/rag/retriever/retriever.py
# 用绝对路径 import 确保无论从哪里调用都能正常工作
import sys
_RAG_ROOT = Path(__file__).parent          # server/rag/
_MCP_ROOT = _RAG_ROOT.parent              # server/
if str(_MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(_MCP_ROOT))

from rag.retriever.retriever import Retriever, RetrievalResponse, SourceType  # noqa: E402


# ── 配置路径 ──────────────────────────────────────────────────────────────────
_SETTINGS_PATH = _RAG_ROOT / "config" / "settings.yaml"


# ── 单例 ──────────────────────────────────────────────────────────────────────
_instance: Optional["RAGService"] = None


def get_rag_service() -> "RAGService":
    """获取 RAGService 单例，首次调用时初始化"""
    global _instance
    if _instance is None:
        _instance = RAGService(_SETTINGS_PATH)
    return _instance


# ── 服务类 ────────────────────────────────────────────────────────────────────

class RAGService:
    """
    RAG 服务，rag.py 里的 MCP 工具通过这里访问所有检索能力。

    设计原则：
      - 每个 query_* 方法对应一类资源，接口语义清晰
      - 资产检索的在线/离线降级在 query_assets 里处理，调用方无感知
      - 返回统一的 RetrievalResponse，格式化工作交给 rag.py
    """

    def __init__(self, settings_path: Path):
        if not settings_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {settings_path}")
        self._settings_path = settings_path
        self._retriever = Retriever.from_settings(settings_path)
        self._docs_answer_service = None

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    async def query_docs(
            self,
            query:       str,
            max_results: int = 5,
    ) -> RetrievalResponse:
        """检索 UE 官方文档"""
        return self._retriever.search(query, SourceType.DOCS, max_results)

    async def answer_docs(
            self,
            query: str,
            history: Optional[list[dict]] = None,
            scene_context: str = "",
            max_results: int = 5,
    ):
        """先检索 docs，再基于检索片段生成最终回答。"""
        retrieval = await self.query_docs(query, max_results=max_results)
        if self._docs_answer_service is None:
            from rag.answer_service import DocsAnswerService

            self._docs_answer_service = DocsAnswerService(self._settings_path)
        return self._docs_answer_service.answer(
            query=query,
            retrieval=retrieval,
            history=history or [],
            scene_context=scene_context,
        )

    async def query_code(
            self,
            query:       str,
            max_results: int = 5,
    ) -> RetrievalResponse:
        """检索项目本地 C++ 源码索引"""
        return self._retriever.search(query, SourceType.CODE, max_results)

    async def query_assets(
            self,
            query:      str,
            asset_type: Optional[str] = None,
            connection=None,
    ) -> RetrievalResponse:
        """
        检索资产。优先在线（通过 UnrealAgent TCP），降级到本地离线索引。

        Args:
            query:      资产名称或关键词
            asset_type: 可选，限定类型（Blueprint / StaticMesh / Material ...）
            connection: UnrealConnection 实例，为 None 时直接走离线模式
        """
        # ── 在线模式 ──────────────────────────────────────────────────────────
        if connection is not None:
            try:
                params = {"query": query}
                if asset_type:
                    params["class_filter"] = asset_type
                raw = await connection.send_request("search_assets", params)
                return self._parse_online_assets(raw, query)
            except Exception:
                pass  # 在线失败 → 静默降级到离线

        # ── 离线模式 ──────────────────────────────────────────────────────────
        response = self._retriever.search(query, SourceType.ASSETS, max_results=5)
        if not response.ok():
            response.error = (
                "资产检索失败：UE Editor 未运行，且本地离线索引不可用。\n"
                "请确认 UE Editor 正在运行，或先运行 asset_indexer.py 构建离线索引。"
            )
        return response

    def get_status(self) -> dict:
        """
        返回各资源类型的就绪状态。
        供 query_docs_status MCP 工具调用。
        """
        return self._retriever.status()

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_online_assets(raw, query: str) -> RetrievalResponse:
        """将 UnrealAgent 返回的在线资产数据转为 RetrievalResponse"""
        from rag.retriever.retriever import RetrievalResult

        if not raw:
            return RetrievalResponse(source=SourceType.ASSETS, query=query)

        assets = raw if isinstance(raw, list) else raw.get("assets", [])
        results = []
        for asset in assets:
            name = asset.get("name", "")
            path = asset.get("path", "")
            cls  = asset.get("class", "")
            results.append(RetrievalResult(
                name    = name,
                score   = 1.0,
                snippet = f"类型: {cls}  路径: {path}",
                source  = SourceType.ASSETS,
                path    = path,
            ))
        return RetrievalResponse(results=results, source=SourceType.ASSETS, query=query)
