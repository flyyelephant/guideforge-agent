"""Scene analysis scripts - migrated from SmartUEAssistant SceneAnalysisTools."""

from ..server import mcp, connection


@mcp.tool()
async def analyze_level_stats() -> dict:
    """分析当前关卡统计：Actor总数、移动性分布、灯光数、顶点/三角面数。"""
    return await connection.send_request("analyze_level_stats", {})


@mcp.tool()
async def find_missing_references() -> dict:
    """查找关卡中有缺失网格或材质引用的 Actor。"""
    return await connection.send_request("find_missing_references", {})


@mcp.tool()
async def find_duplicate_names() -> dict:
    """查找关卡中重复的 Actor 名称。"""
    return await connection.send_request("find_duplicate_names", {})


@mcp.tool()
async def find_oversized_meshes(vertex_threshold: int = 50000) -> dict:
    """查找顶点数超过阈值的高面数网格。"""
    return await connection.send_request("find_oversized_meshes", {"VertexThreshold": vertex_threshold})


@mcp.tool()
async def validate_level() -> dict:
    """验证关卡常见问题：无碰撞、高面数Movable、无阴影灯光、越界Actor。"""
    return await connection.send_request("validate_level", {})
