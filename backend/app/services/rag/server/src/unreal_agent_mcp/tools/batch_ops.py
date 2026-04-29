
"""Batch operation scripts - migrated from SmartUEAssistant BatchOperationTools."""

from ..server import mcp, connection


@mcp.tool()
async def batch_rename_actors(
        prefix: str = "",
        suffix: str = "",
        start_index: int | None = None,    # 改为 Optional
        remove_prefix: str = "",
) -> dict:
    params = {
        "Prefix": prefix,
        "Suffix": suffix,
        "RemovePrefix": remove_prefix,
    }
    if start_index is not None:        # 只有明确传了才加
        params["StartIndex"] = start_index
    return await connection.send_request("batch_rename_actors", params)


@mcp.tool()
async def batch_set_visibility(visible: bool, apply_to_children: bool = True) -> dict:
    """批量设置选中 Actor 的显示/隐藏状态。"""
    return await connection.send_request("batch_set_visibility", {
        "Visible": visible, "ApplyToChildren": apply_to_children,
    })


@mcp.tool()
async def batch_set_mobility(mobility: str) -> dict:
    """批量设置选中 Actor 的移动性：Static / Stationary / Movable。"""
    return await connection.send_request("batch_set_mobility", {"Mobility": mobility})


@mcp.tool()
async def batch_move_to_level(level_name: str) -> dict:
    """将选中的 Actor 移动到指定子关卡。"""
    return await connection.send_request("batch_move_to_level", {"LevelName": level_name})


@mcp.tool()
async def batch_set_tags(tags: list, mode: str = "Set") -> dict:
    """批量设置/追加/移除选中 Actor 的标签。mode: Set / Add / Remove"""
    return await connection.send_request("batch_set_tags", {"Tags": tags, "Mode": mode})


@mcp.tool()
async def align_to_ground(align_rotation: bool = False, offset: float = 0.0) -> dict:
    """将选中 Actor 对齐到地面表面。"""
    return await connection.send_request("align_to_ground", {
        "AlignRotation": align_rotation, "Offset": offset,
    })


@mcp.tool()
async def distribute_actors(
        pattern: str,
        spacing: float,
        columns: int = 5,
        radius: float | None = None,    # None = 让 C++ 自动按 spacing 计算
) -> dict:
    params = {"Pattern": pattern, "Spacing": spacing}
    if pattern.lower() == "grid":
        params["Columns"] = columns
    elif pattern.lower() == "circle" and radius is not None:
        params["Radius"] = radius
    return await connection.send_request("distribute_actors", params)
