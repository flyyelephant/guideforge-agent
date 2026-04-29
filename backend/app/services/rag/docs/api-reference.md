# API Reference

本文档描述 UnrealAgent MCP Server 对外暴露的全部工具接口。

所有工具通过 JSON-RPC 2.0 over TCP 与编辑器通信。

**连接信息**
- 地址：`127.0.0.1:55557`（可在 Project Settings 中修改）
- 协议：Content-Length 分帧的 JSON-RPC 2.0

**Wire Protocol**

```
Content-Length: 64\r\n
\r\n
{"jsonrpc":"2.0","method":"get_project_info","params":{},"id":1}
```

---

## 错误码

| 代码 | 含义 |
|------|------|
| -32700 | Parse Error — JSON 格式无效 |
| -32600 | Invalid Request — 缺少必要字段 |
| -32601 | Method Not Found — 未知方法名 |
| -32602 | Invalid Params — 参数缺失或类型错误 |
| -32603 | Internal Error — 服务器内部错误 |
| -32000 | Server Error — 通用服务端错误 |
| -32001 | Execution Error — 命令执行失败 |

---

## 项目信息

### `get_project_info`
获取当前 UE 项目的详细信息。

**参数：** 无

**返回示例：**
```json
{
  "project_name": "MyProject",
  "engine_version": "5.7.1-48512491",
  "project_dir": "D:/MyProject/",
  "modules": ["MyProject"],
  "plugins": [{"name": "GameplayAbilities", "enabled": true}]
}
```

---

### `get_editor_state`
获取当前编辑器状态。

**参数：** 无

**返回示例：**
```json
{
  "current_level": "MainLevel",
  "world_path": "/Game/Map/MainLevel.MainLevel",
  "is_playing": false,
  "selected_actors": [
    {"name": "PointLight_1", "class": "PointLight", "location": {"x": 0, "y": 0, "z": 300}}
  ],
  "selected_count": 1
}
```

---

## Actor 操作

### `create_actor`
在当前关卡中生成新 Actor。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| class_name | string | ✓ | — | Actor 类名，如 StaticMeshActor、PointLight、DirectionalLight、SpotLight、CameraActor |
| label | string | | "" | 显示标签 |
| location_x/y/z | float | | 0.0 | 世界坐标 |
| rotation_pitch/yaw/roll | float | | 0.0 | 旋转角度（度） |
| scale_x/y/z | float | | 1.0 | 缩放系数 |

**返回示例：**
```json
{"name": "PointLight_1", "class": "PointLight", "location": {"x": 0, "y": 0, "z": 300}, "success": true}
```

---

### `delete_actor`
从当前关卡删除 Actor。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 的 label 或内部名称 |

---

### `select_actors`
在编辑器中选中指定 Actor，传空数组清空选择。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_names | string[] | ✓ | 要选中的 Actor 名称列表 |

**返回示例：**
```json
{"selected": ["PointLight_1"], "selected_count": 1, "not_found": []}
```

---

## 属性读写

### `get_property`
读取 Actor/Component 的任意属性值，支持属性路径解析。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 名称 |
| property_path | string | ✓ | 属性路径，如 `LightComponent.Intensity`、`RootComponent.RelativeLocation.X` |

---

### `set_property`
【精确写入】通过完整属性路径设置单个 Actor/Component 的属性值，支持 Undo。

适用场景：已知确切 Actor 名称和完整属性路径时使用。操作后触发 PostEditChangeProperty 通知，编辑器 UI 同步更新。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 名称，必须精确匹配 |
| property_path | string | ✓ | 属性路径，支持深层路径如 `RootComponent.RelativeLocation.X` |
| value | string/int/float/bool/dict | ✓ | 要设置的值。结构体传 dict，如 `{"x":1,"y":2,"z":3}` |

> **`set_property` vs `modify_property`：**
> - `set_property` — 精确单 Actor，支持深层路径
> - `modify_property` — 模糊多目标（selected / lights / 名称包含某字符串），仅支持顶层属性名

---

### `modify_property`
【模糊修改】通过自然语言目标描述修改 Actor 属性，支持模糊匹配和批量操作。

适用场景：AI 根据用户意图操作时使用（如"把所有灯光变红"）。内置对灯光 LightColor/Intensity 的快速路径处理。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| target | string | ✓ | 目标描述：`selected`/`selection` 当前选中；`light`/`lights` 所有灯光；`Cube_3`/`SM_Wall` 名称包含该字符串的 Actor |
| property_name | string | ✓ | UE 顶层属性名（不支持路径），如 `Intensity`、`LightColor`、`RelativeLocation` |
| value | string/int/float/bool/dict | ✓ | 新值。颜色支持颜色名字符串（中英文），结构体传 dict |

---

### `list_properties`
列出 Actor 或组件的所有可编辑属性。仅返回 EditAnywhere/VisibleAnywhere 标记的属性。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 名称 |
| component_name | string | | 组件名称，留空则列出 Actor 自身属性及其组件列表 |

---

## 世界与关卡

### `get_world_outliner`
获取当前关卡中的所有 Actor。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| class_filter | string | | 按类名过滤，大小写不敏感 |

**返回示例：**
```json
{
  "actors": [
    {
      "name": "DirectionalLight",
      "class": "DirectionalLight",
      "location": {"x": 0, "y": 0, "z": 0},
      "rotation": {"pitch": -67.09, "yaw": -110.38, "roll": -18.83},
      "scale": {"x": 1, "y": 1, "z": 1},
      "is_hidden": false
    }
  ],
  "count": 1,
  "level": "MainLevel"
}
```

---

### `get_current_level`
获取当前关卡信息，包括流式子关卡列表及其加载/可见状态。

**参数：** 无

---

### `get_actor_details`
获取指定 Actor 的详细属性，包括完整变换、组件列表、标签和标志。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 的 label 或内部名称 |

---

## 资产查询（只读）

### `list_assets`
按路径列出项目资产。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| path | string | | /Game | 资产路径 |
| class_filter | string | | "" | 按类名过滤，如 Blueprint、StaticMesh、Material |
| recursive | bool | | true | 是否递归搜索子目录 |

---

### `search_assets`
按名称搜索资产（大小写不敏感）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| query | string | ✓ | 搜索关键词 |
| class_filter | string | | 按类名过滤 |

---

### `get_asset_info`
获取指定资产的详细元数据（名称、类、包路径、标签）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 完整资产路径，如 `/Game/Blueprints/BP_Player` |

---

### `get_asset_references`
获取资产的引用关系图。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 完整资产路径 |

**返回示例：**
```json
{
  "asset_path": "/Game/Blueprints/BP_Player.BP_Player",
  "referencers": ["/Game/Maps/MainLevel"],
  "referencer_count": 1,
  "dependencies": ["/Script/Engine", "/Game/Characters/SKM_Player"],
  "dependency_count": 2
}
```

---

## 资产写操作

### `create_asset`
创建新资产。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_name | string | ✓ | 资产名称 |
| package_path | string | ✓ | 包路径，如 `/Game/Materials` |
| asset_class | string | ✓ | 资产类型：`Material`、`MaterialInstance`、`Blueprint` |
| parent_material | string | | MaterialInstance 的父材质路径 |
| parent_class | string | | Blueprint 的父类名，如 `Actor`、`Character`，默认 `Actor` |

---

### `duplicate_asset`
复制资产到新位置。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| source_path | string | ✓ | 源资产路径 |
| dest_path | string | ✓ | 目标文件夹路径 |
| new_name | string | ✓ | 新资产名称 |

---

### `rename_asset`
重命名或移动资产。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 当前资产路径 |
| new_name | string | | 新名称，可选 |
| new_path | string | | 新目标文件夹路径，可选 |

---

### `delete_asset`
删除资产。默认安全模式：有引用则拒绝。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| asset_path | string | ✓ | — | 要删除的资产路径 |
| force | bool | | false | 是否强制删除（忽略引用检查） |

---

### `save_asset`
保存资产。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | | 传路径则保存单个资产 |
| save_all | bool | | `true` 则保存所有脏资产 |

---

### `create_folder`
在 Content Browser 中创建文件夹。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| folder_path | string | ✓ | 文件夹路径，如 `/Game/Materials/NewFolder` |

---

## Blueprint 操作

### `get_blueprint_overview`
获取蓝图概览：父类、图列表、变量、事件、接口、编译状态。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |

---

### `get_blueprint_graph`
获取蓝图节点图详情：所有节点、引脚、连接关系。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| graph_name | string | | 图名称，留空默认 EventGraph |

---

### `get_blueprint_variables`
获取蓝图所有变量定义（名称、类型、默认值、是否公开、是否复制）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |

---

### `get_blueprint_functions`
获取蓝图自定义函数签名列表（函数名、输入输出参数、是否纯函数）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |

---

### `add_node`
在蓝图图中添加节点。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| node_class | string | ✓ | 节点类型：`CallFunction`、`Event`、`CustomEvent`、`IfThenElse`、`VariableGet`、`VariableSet`、`MacroInstance` |
| graph_name | string | | 图名称，留空默认 EventGraph |
| function_name | string | | CallFunction 时的函数名，如 `PrintString` |
| target_class | string | | CallFunction 时的目标类，如 `KismetSystemLibrary` |
| event_name | string | | Event/CustomEvent 的事件名 |
| variable_name | string | | VariableGet/Set 的变量名 |
| macro_path | string | | MacroInstance 的宏资产路径 |
| node_pos_x/y | int | | 节点坐标 |

---

### `delete_node`
删除蓝图图中指定索引的节点（索引来自 `get_blueprint_graph`）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| node_index | int | ✓ | 节点索引 |
| graph_name | string | | 图名称，留空默认 EventGraph |

---

### `connect_pins`
连接蓝图中两个节点的引脚。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| from_node_index | int | ✓ | 源节点索引 |
| from_pin | string | ✓ | 源节点输出引脚名称 |
| to_node_index | int | ✓ | 目标节点索引 |
| to_pin | string | ✓ | 目标节点输入引脚名称 |
| graph_name | string | | 图名称，留空默认 EventGraph |

---

### `disconnect_pin`
断开蓝图节点某个引脚的所有连接。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| node_index | int | ✓ | 节点索引 |
| pin_name | string | ✓ | 要断开连接的引脚名称 |
| graph_name | string | | 图名称，留空默认 EventGraph |

---

### `add_variable`
向蓝图添加新变量。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| variable_name | string | ✓ | 变量名 |
| variable_type | string | ✓ | 类型：`bool`、`int`、`float`、`string`、`vector`、`rotator`、`transform`、`text`、`name`、`object` |
| default_value | string | | 默认值字符串 |
| category | string | | 变量分类 |
| is_exposed | bool | | 是否公开为 Instance Editable |

---

### `add_function`
向蓝图添加新的自定义函数。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |
| function_name | string | ✓ | 函数名 |
| is_pure | bool | | 是否为纯函数 |

---

### `compile_blueprint`
编译蓝图并返回编译结果（状态、错误列表、警告列表）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 蓝图资产路径 |

---

## 材质操作

### `get_material_graph`
获取完整的材质节点图：所有表达式节点、连接关系和材质属性。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径，如 `/Game/Materials/M_Base` |

---

### `create_material_expression`
在材质图中创建一个表达式节点。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| expression_class | string | ✓ | 表达式类名（不带 U 前缀），如 `MaterialExpressionConstant`、`MaterialExpressionAdd`、`MaterialExpressionCustom` |
| node_pos_x/y | int | | 节点坐标 |

---

### `delete_material_expression`
删除材质图中指定索引的表达式节点。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| expression_index | int | ✓ | 节点索引（来自 get_material_graph） |

---

### `connect_material_property`
将表达式输出连接到材质属性引脚。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| expression_index | int | ✓ | 源表达式索引 |
| property | string | ✓ | 目标材质属性：`MP_BaseColor`、`MP_Metallic`、`MP_Roughness`、`MP_Normal`、`MP_EmissiveColor`、`MP_Opacity`、`MP_OpacityMask`、`MP_AmbientOcclusion` 等 |
| output_name | string | | 输出引脚名称，留空使用默认输出 |

---

### `connect_material_expressions`
连接两个表达式节点：将一个节点的输出连接到另一个节点的输入。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| from_index | int | ✓ | 源表达式索引 |
| to_index | int | ✓ | 目标表达式索引 |
| from_output | string | | 源输出引脚名称，留空使用默认 |
| to_input | string | | 目标输入引脚名称，留空使用默认 |

---

### `set_expression_value`
设置表达式节点的属性值。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| expression_index | int | ✓ | 表达式索引 |
| property_name | string | ✓ | 属性名。Constant → `R`；Constant3Vector → `Constant`；ScalarParameter → `DefaultValue`；TextureSample → `texture_path` |
| value | string | ✓ | JSON 格式的值字符串。颜色传 `{"r":1,"g":0,"b":0,"a":1}` |

---

### `recompile_material`
重编译材质，使修改生效。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |

---

### `layout_material_expressions`
自动排列材质图中的表达式节点为网格布局。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |

---

### `get_material_parameters`
获取材质或材质实例的所有参数名称（scalar、vector、texture、static_switch）。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质或材质实例资产路径 |

---

### `set_material_instance_param`
设置 MaterialInstanceConstant 的参数值。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质实例资产路径 |
| param_name | string | ✓ | 参数名称 |
| param_type | string | ✓ | 参数类型：`scalar`、`vector`、`texture`、`static_switch` |
| value | string | ✓ | 值字符串 |

---

### `set_material_property`
设置材质全局属性。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| asset_path | string | ✓ | 材质资产路径 |
| property_name | string | ✓ | 属性名：`BlendMode`、`ShadingModel`、`TwoSided`、`OpacityMaskClipValue` |
| value | string | ✓ | 值字符串 |

---

## 批量操作

### `batch_rename_actors`
批量重命名当前选中的 Actor。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| prefix | string | | 添加前缀 |
| suffix | string | | 添加后缀 |
| start_index | int | | 序号起始值，传入后追加序号 |
| remove_prefix | string | | 移除名称中的此前缀 |

---

### `batch_set_visibility`
批量设置选中 Actor 的显示/隐藏状态。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| visible | bool | ✓ | 显示或隐藏 |
| apply_to_children | bool | | 是否应用到子 Actor，默认 true |

---

### `batch_set_mobility`
批量设置选中 Actor 的移动性。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| mobility | string | ✓ | `Static`、`Stationary`、`Movable` |

---

### `batch_move_to_level`
将选中 Actor 移动到指定子关卡。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| level_name | string | ✓ | 目标子关卡名称 |

---

### `batch_set_tags`
批量设置/追加/移除选中 Actor 的标签。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| tags | list | ✓ | 标签列表 |
| mode | string | | `Set`（覆盖）、`Add`（追加）、`Remove`（移除），默认 `Set` |

---

### `align_to_ground`
将选中 Actor 对齐到地面表面。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| align_rotation | bool | | 是否同时对齐旋转，默认 false |
| offset | float | | 对齐后的垂直偏移量，默认 0.0 |

---

### `distribute_actors`
按指定模式分布排列选中 Actor。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| pattern | string | ✓ | 分布模式：`grid`（网格）、`circle`（圆形）、`line`（直线） |
| spacing | float | ✓ | 间距 |
| columns | int | | grid 模式的列数，默认 5 |
| radius | float | | circle 模式的半径，留空自动计算 |

---

## 关卡分析

### `analyze_level_stats`
分析当前关卡统计：Actor 总数、移动性分布、灯光数、顶点/三角面数。

**参数：** 无

---

### `find_missing_references`
查找关卡中有缺失网格或材质引用的 Actor。

**参数：** 无

---

### `find_duplicate_names`
查找关卡中重复的 Actor 名称。

**参数：** 无

---

### `find_oversized_meshes`
查找顶点数超过阈值的高面数网格。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| vertex_threshold | int | | 50000 | 顶点数阈值 |

---

### `validate_level`
验证关卡常见问题：无碰撞、高面数 Movable、无阴影灯光、越界 Actor。

**参数：** 无

---

## 编辑器控制

### `undo`
撤销最近的编辑器操作，包括 `execute_python` 的操作。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| steps | int | | 1 | 撤销步数，最大 20 |

---

### `redo`
重做最近撤销的操作。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| steps | int | | 1 | 重做步数，最大 20 |

---

## 上下文感知

### `get_open_editors`
获取当前打开的所有资产编辑器列表（asset_path、asset_name、asset_class、editor_name）。

**参数：** 无

---

### `get_selected_assets`
获取 Content Browser 中当前选中的资产列表（path、name、class）。

**参数：** 无

---

### `get_browser_path`
获取 Content Browser 当前浏览的文件夹路径。

**参数：** 无

---

### `get_message_log`
获取最近的消息日志（包含编译错误、警告等），可按类别和严重级别过滤。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| category | string | | "" | 日志类别过滤，如 `BlueprintLog`、`PIE`、`MaterialEditor`，留空返回所有 |
| count | int | | 50 | 返回条数，最大 200 |
| severity | string | | "" | 严重级别过滤：`Error`、`Warning`、`Log`、`Display`，留空返回所有 |

---

### `get_output_log`
获取输出日志最近 N 条，可按关键字过滤。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| count | int | | 50 | 返回条数，最大 200 |
| filter | string | | "" | 文本过滤关键字 |

---

## 事件

### `get_recent_events`
获取最近的编辑器事件。

事件类型：`SelectionChanged`、`AssetEditorOpened`、`AssetEditorClosed`、`PIEStarted`、`PIEStopped`、`AssetSaved`、`LevelChanged`、`UndoRedo`

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| count | int | | 20 | 返回事件数量，最大 200 |
| type_filter | string | | "" | 按事件类型过滤，可选 |

---

### `get_events_since`
获取指定时间之后的编辑器事件。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| since | string | ✓ | ISO 8601 时间字符串，如 `2026-03-20T10:00:00` |
| type_filter | string | | 按事件类型过滤，可选 |

---

## 视口

### `get_viewport_camera`
获取当前编辑器视口摄像机的位置和旋转。

**参数：** 无

**返回示例：**
```json
{"location": {"x": -266.67, "y": -16.99, "z": 754.51}, "rotation": {"pitch": -55, "yaw": 0, "roll": 0}}
```

---

### `move_viewport_camera`
移动编辑器视口摄像机，只更新传入的参数，其余保持不变。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| location_x/y/z | float | | 摄像机坐标 |
| rotation_pitch/yaw/roll | float | | 摄像机旋转角度（度） |

---

### `focus_on_actor`
将编辑器视口摄像机对准指定 Actor。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| actor_name | string | ✓ | Actor 的 label 或名称 |

---

## 截图

### `take_screenshot`
截取编辑器截图。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| mode | string | | scene | 截图模式：`scene`（视口最终渲染，无 Gizmo，推荐）、`viewport`（含编辑器覆盖物）、`editor`（UI 面板截图） |
| quality | string | | high | 分辨率预设：`low`(512×512)、`medium`(1024×1024)、`high`(1280×720)、`ultra`(1920×1080)，仅 scene/viewport 有效 |
| width/height | int | | 0 | 自定义分辨率，覆盖 quality |
| format | string | | png | 输出格式：`png` 或 `jpg` |
| target | string | | active_window | editor 模式专用：`active_window`、`asset_editor`、`tab`、`full` |
| asset_path | string | | "" | target=asset_editor 时指定资产路径 |
| tab_id | string | | "" | target=tab 时指定面板 ID，如 `LevelEditorSelectionDetails`、`OutputLog` |

---

### `get_asset_thumbnail`
获取资产缩略图并保存为图片文件。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| asset_path | string | ✓ | — | 资产路径 |
| size | int | | 256 | 缩略图尺寸 |

---

### `read_image`
读取图片文件并返回图像内容，供 AI 视觉模块直接查看分析。自动缩放大图控制数据量。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| file_path | string | ✓ | — | 图片文件绝对路径，支持 png、jpg、bmp 等 |
| max_dimension | int | | 800 | 最大边长（像素），超过则等比缩放；设为 0 则不缩放 |

---

## Python 执行

### `execute_python`
在 Unreal Editor 上下文中执行 Python 代码。

上下文有状态——变量、import 和函数定义在多次调用间保持。操作被包装在 Undo 事务中（Ctrl+Z 可撤销）。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| code | string | ✓ | — | 要执行的 Python 代码，支持多行 |
| timeout_seconds | float | | 30.0 | 执行超时（秒），最大 120，防止死循环冻结编辑器 |
| transaction_name | string | | "" | Undo 事务的可读名称，显示在 Edit > Undo History 中 |

**示例：**
```python
import unreal
actors = unreal.EditorLevelLibrary.get_all_level_actors()
print(f"Actor 总数: {len(actors)}")
```

> **注意：** UE 5.7 中 `EditorLevelLibrary` 已标记 deprecated，应改用
> `unreal.get_editor_subsystem(unreal.EditorActorSubsystem)`

---

### `reset_python_context`
重置共享 Python 执行上下文，清除所有变量、import 和函数定义。

**参数：** 无

---

## 构建与启动

### `build_project`
编译 UE 项目（调用 UnrealBuildTool），无需编辑器在运行。

启动编译后立即返回，通过 `get_build_status` 轮询进度。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| uproject_path | string | ✓ | — | `.uproject` 文件的完整路径 |
| configuration | string | | Development | 编译配置：`Development`、`DebugGame`、`Shipping` |
| platform_name | string | | Win64 | 目标平台 |
| clean | bool | | false | 是否执行 Clean Build |

---

### `launch_editor`
启动 UE 编辑器并加载项目，无需编辑器已在运行。如编辑器已运行则直接返回当前状态。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| uproject_path | string | ✓ | — | `.uproject` 文件的完整路径 |
| wait_for_connection | bool | | true | 是否等待 TCP 连接就绪 |
| timeout_seconds | float | | 300.0 | 等待连接就绪的超时时间（秒） |

---

### `build_and_launch`
编译项目并启动编辑器（一条龙）。全程非阻塞，立即返回，通过 `get_build_status` 轮询进度。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| uproject_path | string | ✓ | — | `.uproject` 文件的完整路径 |
| configuration | string | | Development | 编译配置 |
| skip_build | bool | | false | 跳过编译直接启动（已编译过时使用） |

---

### `get_build_status`
查询当前编译状态和进度，同时返回编辑器启动状态（如果正在等待）。

**参数：** 无

**返回示例：**
```json
{
  "status": "building",
  "progress_pct": 45.2,
  "current_target": "UnrealEditor-MyProject.dll",
  "elapsed_seconds": 32.5,
  "recent_output": ["[312/688] Compiling UAActorCommands.cpp"],
  "editor": {"status": "pending", "message": "等待编译完成后启动"}
}
```

---

## 知识库

### `query_knowledge`
在知识库中搜索相关信息。建议在执行操作前调用，查询已知的 API 说明、踩坑记录和最佳实践。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | ✓ | — | 搜索关键词或问题 |
| category | string | | "" | 分类过滤：`api_reference`、`ue_api_gotchas`、`tool_schemas`、`lessons_learned`、`best_practices` |
| tags | string | | "" | 逗号分隔的标签过滤 |
| top_k | int | | 10 | 最多返回条数 |

---

### `save_knowledge`
将新知识保存到知识库。用于记录解决新问题后的经验，供后续参考。

AI 只能写入 `lessons_learned` 和 `best_practices` 两个分类。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| title | string | ✓ | — | 简短描述性标题 |
| content | string | ✓ | — | 详细说明，包含问题、根因、解决方案 |
| category | string | | lessons_learned | 分类：`lessons_learned` 或 `best_practices` |
| tags | string | | "" | 逗号分隔的标签，如 `material,custom-node` |
| ue_version | string | | "" | 适用的 UE 版本，如 `5.7` |
| confidence | float | | 0.8 | 可信度 0-1 |

---

### `get_knowledge_stats`
获取知识库统计信息（条目总数、分类列表、索引大小）。

**参数：** 无

---

## RAG 检索

### `query_docs_status`
查看 RAG 文档知识库当前状态，确认各类资源是否已正确加载。

**参数：** 无

---

### `query_docs`
查询 UE 官方文档知识库。适用于 UE API、Blueprint、C++ 编程规范、编辑器操作等问题。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | ✓ | — | 查询内容，支持中英文 |
| max_results | int | | 5 | 返回结果数量，最大 10 |

---

### `query_code`
查询项目本地 C++ 源码索引（UnrealAgent + SmartUEAssistant 插件）。适用于查找类定义、函数实现位置、注释说明等。

| 参数 | 类型 | 必须 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | ✓ | — | 查询内容，建议使用英文类名或函数名 |
| max_results | int | | 5 | 返回结果数量 |

---

### `query_assets`
在 UE 项目中搜索资产（材质、蓝图、静态网格等）。优先通过 UnrealAgent 实时查询，编辑器未运行时自动切换到本地离线索引。

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| query | string | ✓ | 资产名称或关键词，如 `M_Rock`、`BP_Player` |
| asset_type | string | | 限定资产类型：`Blueprint`、`StaticMesh`、`Material`、`Texture2D` |