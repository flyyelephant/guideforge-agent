"""Universal property read/write scripts — based on UE reflection system."""

from ..server import mcp, connection


@mcp.tool()
async def get_property(actor_name: str, property_path: str) -> dict:
    """读取 Actor/Component 的任意属性值。

    通过 UE 反射系统支持属性路径解析，可以读取任何可编辑属性。

    Args:
        actor_name: Actor 名称（label 或内部名）。
        property_path: 属性路径，格式: 'ComponentName.PropertyName' 或
                       'ComponentName.StructProp.Field'。
                       如果只提供属性名（无点号），则直接在 Actor 上查找。
                       示例: 'LightComponent.Intensity',
                             'StaticMeshComponent.StaticMesh',
                             'RootComponent.RelativeLocation.X'
    """
    return await connection.send_request(
        "get_property",
        {"actor_name": actor_name, "property_path": property_path},
    )


@mcp.tool()
async def set_property(
    actor_name: str,
    property_path: str,
    value: str | int | float | bool | dict,
) -> dict:
    """【精确写入】通过完整属性路径设置单个 Actor/Component 的属性值。支持 Undo。

    适用场景：已知确切的 Actor 名称和完整属性路径时使用。
    操作后会触发 PostEditChangeProperty 通知，保证编辑器 UI 同步更新。

    与 modify_property 的区别：
    - set_property   → 精确单 Actor、支持深层路径（如 'LightComponent.Intensity'）
    - modify_property → 模糊多目标（'selected' / 'all lights'）、仅顶层属性名

    Args:
        actor_name:    Actor 名称（label 或内部名），必须精确匹配。
        property_path: 属性路径，与 get_property 格式相同。
                       支持深层路径，如 'RootComponent.RelativeLocation.X'。
        value:         要设置的值。数值传数字，字符串传字符串，布尔传 true/false，
                       结构体（如 FVector）传 dict: {"x":1,"y":2,"z":3}，
                       对象引用传资产路径字符串。
    """
    return await connection.send_request(
        "set_property",
        {"actor_name": actor_name, "property_path": property_path, "value": value},
    )


@mcp.tool()
async def list_properties(actor_name: str, component_name: str = "") -> dict:
    """列出 Actor 或组件的所有可编辑属性。

    返回名称、类型、当前值预览、是否可编辑。
    仅列出 EditAnywhere/VisibleAnywhere 标记的属性。

    Args:
        actor_name:     Actor 名称（label 或内部名）。
        component_name: 组件名称。留空列出 Actor 自身的属性及其组件列表。
    """
    params: dict = {"actor_name": actor_name}
    if component_name:
        params["component_name"] = component_name
    return await connection.send_request("list_properties", params)


@mcp.tool()
async def modify_property(
    target: str,
    property_name: str,
    value: str | int | float | bool | dict,
) -> dict:
    """【语义修改】通过自然语言目标描述修改 Actor 属性，支持模糊匹配和批量操作。

    适用场景：AI 根据用户意图操作时使用（如"把所有灯光变红"）。
    内置对灯光 LightColor/Intensity 的快速路径处理。

    与 set_property 的区别：
    - modify_property → 模糊目标匹配、可同时修改多个 Actor、仅支持顶层属性名
    - set_property    → 精确单 Actor、完整深层路径、适合编程式精确控制

    Args:
        target:        目标描述（模糊匹配），支持：
                       'selected' / 'selection' — 当前选中的 Actor
                       'light' / 'lights'       — 场景中所有灯光
                       'Cube_3' / 'SM_Wall'     — 名称包含该字符串的 Actor
        property_name: UE 顶层属性名（不支持路径），如 'Intensity'、
                       'LightColor'、'RelativeLocation'。
        value:         新值。数值/布尔/字符串颜色名/{"X":1,"Y":2,"Z":3} 结构体。
    """
    return await connection.send_request(
        "modify_property",
        {"Target": target, "PropertyName": property_name, "Value": value},
    )
