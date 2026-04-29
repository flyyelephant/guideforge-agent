"""
RAG MCP 工具层

职责：
  - 注册 MCP 工具（@mcp.tool 装饰器）
  - 调用 RAGService，把结果格式化为字符串返回给 AI
  - 不写任何检索逻辑，不拼路径，不处理降级

设计原则：
  每个工具函数只做两件事：
    1. 调用 service 的对应方法
    2. 调用 _format_response() 格式化结果

关于跨包 import：
  rag/ 目录在 server/ 下，不在 src/ 包内，
  无法用相对 import，通过 sys.path 注入解决，
  这是唯一需要动 sys.path 的地方。
"""

import sys
from pathlib import Path

from ..server import mcp, connection

# ── 跨包导入：把 server/ 加入 sys.path ─────────────────────────────────────
# 本文件: server/src/unreal_agent_mcp/scripts/rag.py
# 目标:   server/rag/service.py
_MCP_ROOT = Path(__file__).parent.parent.parent.parent  # server/
if str(_MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(_MCP_ROOT))

from rag.service import get_rag_service          # noqa: E402
from rag.retriever import RetrievalResponse, SourceType  # noqa: E402


# ── 格式化 ────────────────────────────────────────────────────────────────────

def _format_response(response: RetrievalResponse) -> str:
    """
    将 RetrievalResponse 统一格式化为 AI 可读的字符串。
    所有工具共用同一套格式，保持 AI 侧体验一致。
    """
    if not response.ok():
        return f"❌ {response.error}"

    if response.empty():
        hints = {
            SourceType.DOCS:   "建议换用英文关键词，或拆分为更短的词组",
            SourceType.CODE:   "建议使用英文类名或函数名，例如 'UABatchOperationCommands'",
            SourceType.ASSETS: "建议使用资产名前缀，例如 'BP_' 'M_' 'SM_'",
        }
        hint = hints.get(response.source, "请尝试其他关键词")
        return f"未找到与「{response.query}」相关的内容。\n{hint}"

    source_label = {
        SourceType.DOCS:   "UE 文档",
        SourceType.CODE:   "C++ 源码",
        SourceType.ASSETS: "资产",
    }.get(response.source, "内容")

    lines = [f"找到 {len(response.results)} 条相关{source_label}（查询：{response.query}）\n"]
    for i, r in enumerate(response.results, 1):
        lines.append(f"[{i}] {r.name}  (相关度: {r.score})")
        if r.snippet:
            lines.append(f"    {r.snippet}...")
        lines.append("")

    return "\n".join(lines)


def _format_answer_response(response) -> str:
    """Format the final grounded answer returned by the answer layer."""
    if not response.ok():
        body = f"❌ {response.error}\n\n{response.answer}"
    else:
        body = response.answer

    if not getattr(response, "sources", None):
        return body

    lines = [body, "", "参考来源："]
    for index, item in enumerate(response.sources, start=1):
        lines.append(f"[{index}] {item.name}")
        if item.path:
            lines.append(f"    {item.path}")
    return "\n".join(lines)


# ── MCP 工具 ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def query_docs_status() -> str:
    """查看 RAG 文档知识库当前状态，确认各类资源是否已正确加载。"""
    service = get_rag_service()
    status  = service.get_status()

    lines = ["RAG 知识库状态\n"]
    label_map = {
        "docs":   "UE 官方文档",
        "code":   "C++ 源码索引",
        "assets": "资产离线索引",
    }
    for source, info in status.items():
        label = label_map.get(source, source)
        if info["ready"]:
            lines.append(f"  ✅ {label}：已就绪，{info['doc_count']} 个文件")
        else:
            lines.append(f"  ❌ {label}：{info['error']}")

    return "\n".join(lines)


@mcp.tool()
async def query_docs(query: str, max_results: int = 5) -> str:
    """
    查询 UE 官方文档知识库。
    适用于：UE API、Blueprint、C++ 编程规范、编辑器操作等问题。

    Args:
        query:       查询内容，支持中英文。例如："Actor BeginPlay 调用时机"
        max_results: 返回结果数量，默认 5，最多 10
    """
    service  = get_rag_service()
    response = await service.query_docs(query, max_results)
    return _format_response(response)


@mcp.tool()
async def answer_docs(query: str, max_results: int = 5) -> str:
    """
    先检索 UE 文档，再基于命中的文档片段生成最终回答。
    适合直接用于智能客服问答，而不是只看原始检索结果。
    """
    service = get_rag_service()
    response = await service.answer_docs(query, max_results=max_results)
    return _format_answer_response(response)


@mcp.tool()
async def query_code(query: str, max_results: int = 5) -> str:
    """
    查询项目本地 C++ 源码索引（UnrealAgent + SmartUEAssistant 插件）。
    适用于：查找类定义、函数实现位置、注释说明等。

    Args:
        query:       查询内容，例如："UABatchOperationCommands 批量重命名"
        max_results: 返回结果数量，默认 5
    """
    service  = get_rag_service()
    response = await service.query_code(query, max_results)
    return _format_response(response)


@mcp.tool()
async def query_assets(query: str, asset_type: str = None) -> str:
    """
    在 UE 项目中检索资产（材质、蓝图、静态网格等）。
    优先通过 UnrealAgent 实时查询，UE Editor 未运行时自动切换到本地离线索引。

    Args:
        query:      资产名称或关键词，例如："M_Rock" "BP_Player"
        asset_type: 可选，限定资产类型：Blueprint / StaticMesh / Material / Texture2D
    """
    service  = get_rag_service()
    response = await service.query_assets(query, asset_type, connection)
    return _format_response(response)
