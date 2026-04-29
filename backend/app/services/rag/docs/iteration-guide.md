# 迭代开发指南

本文说明如何在当前项目结构内持续迭代，覆盖三条主要迭代轴的改动位置、流程和注意事项。

---

## 项目迭代的三条轴

| 轴 | 目标 | 主要改动位置 |
|---|---|---|
| 轴一：扩展编辑器操控能力 | 让 AI 能执行更多编辑器操作 | `Plugins/UnrealAgent/` + `server/tools/` |
| 轴二：增强知识检索 | 让 AI 能检索更多本地知识 | `server/rag/` + `knowledge/` |
| 轴三：改善对话体验 | 让 AI 回答质量更好 | `server/src/` + `Plugins/SmartUEAssistant/` |

三条轴之间相互独立，可以并行推进。

---

## 轴一：扩展编辑器操控能力

每新增一类编辑器操作，需要同时改动 **C++ 命令层** 和 **Python 工具层**，缺一不可。

### 第一步：新增 C++ 命令

在 `Plugins/UnrealAgent/Source/UnrealAgent/Private/Commands/` 新建命令文件。

命名规范：`UA{领域}Commands.cpp / .h`，例如 `UANiagaraCommands.cpp`。

`.h` 文件结构：

```cpp
// UANiagaraCommands.h
#pragma once
#include "CoreMinimal.h"
#include "Commands/UACommandBase.h"

class FUANiagaraCommands : public FUACommandBase
{
public:
    virtual void RegisterCommands(FUACommandRegistry& Registry) override;
};
```

`.cpp` 文件结构：

```cpp
// UANiagaraCommands.cpp
#include "UANiagaraCommands.h"

void FUANiagaraCommands::RegisterCommands(FUACommandRegistry& Registry)
{
    Registry.Register("create_niagara_system",
        [this](const TSharedPtr<FJsonObject>& Params) -> TSharedPtr<FJsonObject>
        {
            // 从 Params 读取参数
            FString AssetPath = Params->GetStringField(TEXT("asset_path"));

            // 调用 UE API 实现逻辑

            // 构造并返回结果
            TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
            Result->SetBoolField(TEXT("success"), true);
            return Result;
        });
}
```

然后在 `UACommandRegistry.cpp` 里注册新模块：

```cpp
#include "Commands/UANiagaraCommands.h"

// 在 RegisterAllCommands() 里加入：
RegisterModule<FUANiagaraCommands>();
```

### 第二步：新增 Python MCP 工具

在 `server/src/unreal_agent_mcp/tools/` 新建工具文件。

```python
# server/src/unreal_agent_mcp/tools/niagara.py
"""Niagara particle system tools."""

from ..server import mcp, connection


@mcp.tool()
async def create_niagara_system(
    asset_path: str,
    template: str = "",
) -> dict:
    """创建 Niagara 粒子系统资产。

    Args:
        asset_path: 目标资产路径，如 /Game/Effects/NS_Fire
        template: 可选模板名称
    """
    params = {"asset_path": asset_path}
    if template:
        params["template"] = template
    return await connection.send_request("create_niagara_system", params)
```

**工具文件只做两件事：参数组装 + 调用 `connection.send_request()`。不包含任何业务逻辑。** 如果工具文件越写越重，说明逻辑还没有下沉到 C++ 命令层。

### 第三步：在入口处注册

打开 `server/src/unreal_agent_mcp/__main__.py`，在 import 列表里加入新模块：

```python
from .tools import (
    # ... 已有模块 ...
    niagara,  # 新增
)
```

### 第四步：重新生成项目文件并编译

新增 C++ 文件后必须执行此步，否则 UBT 找不到新文件：

1. 右键 `SmartUEAssistant.uproject` → **Generate Visual Studio project files**
2. 在 Visual Studio 里重新编译（或在编辑器里 Live Coding）
3. 重启编辑器加载新插件版本

### 命令拆分原则

参考现有命令的拆分方式：

| 情况 | 做法 |
|---|---|
| 新领域（如 Niagara、Sequencer） | 新建独立命令文件 |
| 现有领域的新操作 | 在已有命令文件里追加 `Register` 调用 |
| 单个命令文件超过 500 行 | 参考 `UABlueprintCommands` 的做法，把写操作拆到 `_Operations` 后缀文件 |

---

## 轴二：增强知识检索

知识检索有三个独立的索引源，可以分别扩展，互不影响。

### C++ 源码索引

**触发时机：** 插件源码新增或修改了类/函数后。

```bash
cd server/rag/indexers
python cpp_indexer.py
```

索引器扫描 `settings.yaml` 里 `project_source_path` 指向的目录（当前为 `Plugins/`），为每个 `.cpp` 和 `.h` 生成摘要 markdown，输出到 `knowledge/cpp_source/converted/`，然后重建向量索引。

**提升索引质量：** 如果 AI 对代码相关问题的回答质量不好，可以修改 `cpp_indexer.py` 调整摘要生成策略，例如增加函数体关键逻辑的提取、或补充跨文件的调用关系。

### UE 文档索引

**扩展来源：** 把自定义文档（引擎修改说明、项目规范等）放入 `knowledge/ue_docs/raw/markdown/`，格式为标准 markdown。

```bash
# 若有 udn 格式文档，先转换
cd server/rag/scripts/converters
python udn_to_markdown.py

# 重建向量索引
cd server/rag/pageindex/scripts
python build_index.py
```

**调整分类规则：** `settings.yaml` 的 `categorization` 段控制文档分类，分类决定 `qa_agent` 和 `ue_dev_agent` 各自优先检索哪些文档。根据实际文档内容调整规则：

```yaml
categorization:
  engine-modification:        # 新增一个分类
    - "EngineModification"
    - "CustomEngine"
    - "引擎修改"
```

### 资产索引

资产索引目前尚未启用（`knowledge/project_assets/` 为空）。启用步骤：

1. 确认 `settings.yaml` 里 `assets_output_dir` 指向 `../../knowledge/project_assets`
2. 确保编辑器正在运行（索引器需通过 TCP 查询资产信息）
3. 运行索引器：

```bash
cd server/rag/indexers
python asset_indexer.py
```

启用后，AI 可以回答"项目里有没有叫 xxx 的材质"、"找一个 StaticMesh 类型的资产"等问题。

### 添加全新索引源

如果需要索引 Confluence 文档、Notion 导出、内部 Wiki 等外部来源，按以下步骤：

**1. 新建索引器**

在 `server/rag/indexers/` 新建 `xxx_indexer.py`，输出 markdown 到 `knowledge/` 下的新子目录：

```python
# server/rag/indexers/confluence_indexer.py

OUTPUT_DIR = "../../knowledge/confluence_docs/converted"

def index_confluence_pages():
    # 拉取文档内容
    # 转为 markdown
    # 写入 OUTPUT_DIR
    pass
```

**2. 更新配置**

在 `settings.yaml` 加入新路径：

```yaml
confluence_docs:
  converted_path: ../../knowledge/confluence_docs/converted
```

**3. 注册进检索路由**

在 `server/rag/service.py` 里把新索引源加入检索逻辑。

**4. 加入索引构建流程**

在 `server/rag/pageindex/scripts/build_index.py` 里把新目录纳入构建。

**5. 更新 .gitignore**

在根目录 `.gitignore` 加入：

```gitignore
knowledge/confluence_docs/converted/
```

---

## 轴三：改善对话体验

这一轴几乎全在 Python 服务层，不需要动 C++ 代码。

### 调整系统提示

HTTP 模式的系统提示在 `server/src/unreal_agent_mcp/app.py`。如果 AI 在某类操作上持续出错（比如总是生成错误的属性路径），在系统提示里加具体的约束说明是最直接的修法：

```python
SYSTEM_PROMPT = """
你是 Unreal Engine 5 的 AI 助手。

# 属性路径规范
- 修改光源颜色时使用路径：LightComponent.LightColor（不是 Color）
- 修改光源强度时使用路径：LightComponent.Intensity

# 工具使用原则
- 操作前先用 get_asset_info 确认资产存在
- ...
"""
```

### 调整场景上下文

`Plugins/SmartUEAssistant/Source/SmartUEAssistant/Private/SceneContextProvider.cpp` 控制每次发消息时附带什么场景信息。当前采集选中 Actor 列表、关卡名等基础信息。

如果 AI 经常因为缺少某类信息而给出错误回答，在 `SceneContextProvider` 里加采集逻辑：

```cpp
// 示例：额外采集选中 Actor 的变换信息
if (SelectedActor)
{
    FTransform Transform = SelectedActor->GetActorTransform();
    // 序列化到 SceneContext 字符串
}
```

**注意采集粒度：** 场景上下文越详细，token 消耗越高，响应越慢。只采集 AI 真正会用到的信息。

### 维护本地知识条目

`knowledge_store.py` 管理的是手动维护的结构化知识，适合存放项目专有约定——这类信息不在代码里，但需要 AI 知道，例如：

- 命名规范：`所有光源 Actor 命名为 Light_xxx`
- 目录约定：`角色蓝图统一放在 /Game/Characters/Blueprints/`
- 禁止操作：`不允许直接删除 /Game/Core/ 下的资产`

通过 `knowledge` MCP 工具读写，或者直接编辑 JSON 文件。

---

## 容易踩坑的地方

### 坑一：C++ 改完忘记重新生成项目文件

任何新增或删除 C++ 文件后，必须右键 `.uproject` → **Generate Visual Studio project files**，再重新编译。否则 UBT 找不到新文件，编译会报奇怪的错误。

### 坑二：RAG 索引与源码不同步

`knowledge/cpp_source/converted/` 是某个时间点的快照。插件代码改了之后 RAG 检索的内容仍然是旧的，直到手动重跑 `cpp_indexer.py`。

建议在 `knowledge/index_cache/.index_cache.json` 里维护一个 `last_indexed_at` 字段，`cpp_indexer.py` 写入时更新，`service.py` 启动时读取并打印日志，方便排查索引是否过期：

```
[RAG] 当前 C++ 索引时间：2026-03-19 02:44，距今 1 天
```

### 坑三：工具注册顺序

`__main__.py` 里的 import 顺序决定工具注册顺序，影响 MCP 工具列表的展示顺序。建议按领域分组排列，保持可读性，新工具加在对应分组末尾。

### 坑四：TCP 连接未就绪时运行索引器

`asset_indexer.py` 需要编辑器在运行（TCP :55557 就绪）才能执行。`cpp_indexer.py` 和 `doc_indexer.py` 则完全离线，不依赖编辑器。注意区分。

---

## 迭代节奏建议

### 近期：补全资产索引

当前 RAG 三个索引源中，资产索引尚未启用，是最明显的缺口。优先把 `asset_indexer.py` 跑起来，让 AI 能回答项目资产相关的问题。

### 中期：评估检索质量

用 `simple_rag_query.py` 跑几十个典型问题，评估 RAG 命中率：

```bash
cd server/rag/scripts
python simple_rag_query.py "如何获取 Actor 的位置"
python simple_rag_query.py "点光源的强度属性叫什么"
python simple_rag_query.py "项目里有哪些角色蓝图"
```

命中率低的常见原因：
- `cpp_indexer.py` 生成的摘要过于简短，丢失了关键信息
- `build_index.py` 的文档分块策略不合适，把相关内容切断了
- 查询的内容根本没有被索引（用 `simple_rag_query.py` 的调试模式确认）

### 长期：按需扩展命令

根据团队使用中遇到的"AI 做不到"的操作，按轴一流程补充 C++ 命令和 Python 工具。优先补充高频、手动做繁琐的操作——批量操作类和跨资产的关系查询通常收益最高。

---

## 快速参考

### 新增编辑器命令

```
1. Plugins/UnrealAgent/.../Commands/ 新建 UA{领域}Commands.cpp/.h
2. UACommandRegistry.cpp 里注册新模块
3. server/tools/ 新建对应工具文件（只做参数转发）
4. __main__.py import 列表加入新模块
5. 右键 .uproject → Generate VS project files → 重新编译
```

### 更新知识索引

```
修改了 C++ 源码：
  cd server/rag/indexers && python cpp_indexer.py

新增了文档：
  把文档放入 knowledge/ue_docs/raw/markdown/
  cd server/rag/pageindex/scripts && python build_index.py

需要资产索引（编辑器运行时）：
  cd server/rag/indexers && python asset_indexer.py
```

### 调试 RAG 检索

```bash
cd server/rag/scripts
python simple_rag_query.py "你的查询内容"
```

### 调试 MCP 工具

```bash
cd server
python -m unreal_agent_mcp  # stdio 模式，配合 Claude Desktop 使用

# 或 HTTP 模式，用 curl 直接调试
SMART_UE_MODE=http python -m unreal_agent_mcp
curl -X POST http://127.0.0.1:8765/chat \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "列出场景里所有的灯光", "history": [], "scene_context": ""}'
```