# Smart UE Assistant

Smart UE Assistant 是一个面向 Unreal Engine 的本地 AI 助手项目。当前仓库已经打通一条可运行的 UE 文档问答主线，包括文档清洗与加载、分块、向量化、关键词索引、混合检索、答案生成，以及本地网页聊天入口。

项目重点不是通用聊天，而是围绕 Unreal Engine 文档和编辑器工作流提供可落地的辅助能力。当前最稳定的能力是基于 UE 文档知识库进行问答，并返回可追溯的来源文件。

## 当前能力

- 支持 UE 文档知识库接入，覆盖 `markdown` 和 `udn`
- 支持文档分块、向量化、本地向量库存储
- 支持关键词索引和混合检索
- 支持基于检索结果生成中文答案
- 支持本地 HTTP 聊天入口和简易网页聊天页
- 支持 MCP 工具层中的 docs 查询与 docs 问答链路

当前更适合回答：

- UE 类型说明和核心概念说明
- 编辑器功能说明
- README / Guide / Reference 类问题
- 已经进入知识库的官方文档内容

## 技术方案

当前问答链路使用的关键技术和模型：

- 文档加载：本地 `markdown / udn / txt / pdf`
- 文本切块：递归切块
- 向量模型：`text-embedding-v4`
- 问答模型：`qwen-plus`
- 向量库：`Chroma`
- 关键词检索：`BM25 + jieba`
- 检索策略：稠密检索 + 稀疏检索混合召回
- 服务接口：`FastAPI`

## 项目结构

下面这部分按当前仓库实际结构整理，重点把新增的 `server/rag/modular` 主线展开说明。

```text
smart_ue_assistant-main/
├─ SmartUEAssistant.uproject                     # UE 项目文件
├─ LICENSE                                       # MIT License
├─ README.md
├─ .gitignore
├─ Config/                                       # UE 工程配置
├─ docs/                                         # 设计文档
│  ├─ api-reference.md
│  ├─ design-build-and-launch.md
│  ├─ design-universal-execution.md
│  ├─ expansion-plan.md
│  ├─ knowledge-base-design.md
│  └─ test-plan.md
├─ Plugins/
│  ├─ UnrealAgent/                               # 编辑器执行层插件（C++）
│  │  ├─ UnrealAgent.uplugin
│  │  ├─ Config/
│  │  └─ Source/UnrealAgent/
│  │     ├─ Private/
│  │     │  ├─ Commands/                         # 编辑器命令模块
│  │     │  ├─ Protocol/                         # JSON-RPC 协议与路由
│  │     │  ├─ Server/                           # TCP Server / Client Connection
│  │     │  └─ Settings/                         # 插件配置
│  │     └─ Public/
│  └─ SmartUEAssistant/                          # 编辑器 UI 插件（C++）
│     ├─ SmartUEAssistant.uplugin
│     ├─ Config/
│     ├─ doc/
│     └─ Source/SmartUEAssistant/
│        ├─ Private/
│        │  ├─ AIAssistantWindow.cpp             # Slate 聊天窗口
│        │  ├─ AIService.cpp                     # HTTP / SSE 客户端
│        │  ├─ SceneContextProvider.cpp          # 场景上下文采集
│        │  └─ ConsoleCommandWhitelist.cpp       # 控制台命令白名单
│        └─ Public/
├─ server/                                       # Python 服务层
│  ├─ pyproject.toml
│  ├─ src/unreal_agent_mcp/                      # MCP / HTTP 服务入口
│  │  ├─ __main__.py                             # 入口，按 SMART_UE_MODE 分流
│  │  ├─ app.py                                  # FastAPI HTTP Gateway + 浏览器聊天页
│  │  ├─ http_server.py                          # HTTP 服务启动
│  │  ├─ server.py                               # MCP Server 实例
│  │  ├─ connection.py                           # UnrealAgent TCP 连接
│  │  ├─ knowledge_store.py                      # 本地知识缓存
│  │  ├─ ast_fingerprint.py                      # 代码变更检测
│  │  ├─ telemetry.py                            # 工具调用统计
│  │  └─ tools/                                  # MCP 工具集合
│  │     ├─ actors.py
│  │     ├─ asset_query.py
│  │     ├─ asset_write.py
│  │     ├─ blueprints.py
│  │     ├─ build.py
│  │     ├─ context.py
│  │     ├─ editor.py
│  │     ├─ knowledge.py
│  │     ├─ materials.py
│  │     ├─ project.py
│  │     ├─ properties.py
│  │     ├─ python.py
│  │     ├─ rag.py
│  │     ├─ scene_analysis.py
│  │     ├─ screenshots.py
│  │     ├─ viewport.py
│  │     └─ world.py
│  └─ rag/                                       # 检索与问答主线
│     ├─ answer_service.py                       # 检索后答案生成
│     ├─ service.py                              # 对外统一 RAG 服务
│     ├─ config/settings.yaml                    # 外层业务配置
│     ├─ retriever/
│     │  ├─ retriever.py                         # 检索入口
│     │  └─ modular_backend.py                   # 底层检索适配层
│     ├─ scripts/
│     │  ├─ build_modular_indexes.py             # docs 索引构建脚本
│     │  ├─ simple_rag_query.py                  # 本地查询验证脚本
│     │  ├─ collectors/                          # 文档收集脚本
│     │  └─ converters/                          # 文档转换脚本
│     ├─ indexers/                               # 旧索引脚本保留区
│     ├─ pageindex/
│     └─ modular/                                # 新增的文档处理与检索运行时核心
│        ├─ config/
│        │  ├─ settings.yaml                     # 底层模型、检索、向量库配置
│        │  └─ prompts/                          # chunk 精炼、metadata、rerank 等提示词
│        ├─ data/                                # 本地数据目录，默认不提交
│        │  ├─ db/
│        │  │  ├─ chroma/                        # Chroma 向量库
│        │  │  ├─ bm25/                          # BM25 索引
│        │  │  ├─ ingestion_history.db           # 入库历史
│        │  │  └─ image_index.db
│        │  └─ images/
│        └─ src/
│           ├─ core/                             # Settings、类型、查询引擎、响应组装
│           │  ├─ query_engine/
│           │  │  ├─ dense_retriever.py
│           │  │  ├─ sparse_retriever.py
│           │  │  ├─ hybrid_search.py
│           │  │  ├─ query_processor.py
│           │  │  ├─ fusion.py
│           │  │  └─ reranker.py
│           │  ├─ response/
│           │  └─ trace/
│           ├─ ingestion/                        # 文档入库主线
│           │  ├─ document_manager.py
│           │  ├─ pipeline.py                    # loader -> chunk -> embedding -> upsert
│           │  ├─ chunking/
│           │  │  └─ document_chunker.py
│           │  ├─ embedding/
│           │  │  ├─ dense_encoder.py
│           │  │  ├─ sparse_encoder.py
│           │  │  └─ batch_processor.py
│           │  ├─ storage/
│           │  │  ├─ vector_upserter.py
│           │  │  └─ bm25_indexer.py
│           │  └─ transform/
│           ├─ libs/                             # 模型与基础组件工厂层
│           │  ├─ embedding/
│           │  ├─ llm/
│           │  ├─ loader/
│           │  ├─ reranker/
│           │  ├─ splitter/
│           │  └─ vector_store/
│           ├─ mcp_server/                       # 底层 MCP Server 与知识查询工具
│           └─ observability/                    # 评测、日志、可观测性
└─ knowledge/                                    # 本地知识库源数据
   └─ ue_docs/
      └─ raw/
         ├─ markdown/                            # Markdown 文档
         └─ udn/                                 # UE 原始 UDN 文档
```

### `server/rag/modular` 在当前仓库里的作用

这部分是这次集成里最核心的新内容。它负责把原先项目里的文档问答能力补成一条完整的 RAG 主线：

- 文档加载：支持 `markdown / udn / txt / pdf`
- 文档切块：统一 chunk 规则
- 向量化：调用 embedding 模型生成向量
- 稀疏索引：构建 BM25 关键词索引
- 向量入库：写入本地 Chroma
- 混合检索：把 dense / sparse 结果融合
- 问答生成：把检索结果喂给问答模型生成最终答案

外层的 `server/rag/service.py` 和 `server/rag/retriever/modular_backend.py` 负责把这套运行时接到原项目现有接口上，因此 UE 侧和 MCP 工具层不用大改。

## 环境要求

- Python `3.10+`
- Windows
- 可用的通义 API Key

如果你只使用当前文档问答链路，核心依赖已经写在 [server/pyproject.toml](server/pyproject.toml)。

## 安装

```powershell
cd server
pip install -e .
```

建议使用环境变量配置模型密钥，不要把真实密钥直接提交到仓库：

```powershell
setx OPENAI_API_KEY "your_dashscope_compatible_key"
```

说明：

- 当前代码走的是通义兼容 OpenAI 接口
- 因此默认读取 `OPENAI_API_KEY`

## 配置说明

外层项目配置：

- [server/rag/config/settings.yaml](server/rag/config/settings.yaml)

这层主要控制：

- 当前使用哪个检索后端
- docs collection 的输入目录
- 业务层路径映射

底层检索与模型配置：

- [server/rag/modular/config/settings.yaml](server/rag/modular/config/settings.yaml)

这层主要控制：

- 向量模型
- 问答模型
- 向量库存储路径
- 检索参数
- 分块参数

## 构建文档索引

首次运行前，需要先把 UE 文档建入本地索引：

```powershell
cd smart_ue_assistant-main
python server\rag\scripts\build_modular_indexes.py --source docs --force
```

当前 docs 索引会读取：

- `knowledge/ue_docs/raw/markdown`
- `knowledge/ue_docs/raw/udn`

建库完成后，就可以对 UE 文档做本地检索和问答。

## 启动聊天服务

最简单的启动方式：

```powershell
cd server
python -m unreal_agent_mcp
```

如果你只想启动 HTTP 聊天入口：

```powershell
$env:SMART_UE_MODE="http"
python -m unreal_agent_mcp
```

默认地址：

```text
http://127.0.0.1:8765
```

浏览器打开根路径即可进入简易聊天页：

```text
http://127.0.0.1:8765/
```

## Chat API

接口：

- `POST /chat`

请求示例：

```json
{
  "message": "Actor 是什么？",
  "history": [],
  "scene_context": ""
}
```

返回示例：

```json
{
  "response": "AActor 是 Unreal Engine 中可放入场景的对象基类……",
  "sources": [
    {
      "name": "AActor",
      "path": "knowledge/ue_docs/raw/udn/Source_Shared_Types_AActor_AActor.INT.udn",
      "score": 0.91
    }
  ],
  "error": null
}
```

## 建议测试问题

- `Actor 是什么？`
- `AActor 是什么？`
- `StaticMesh 是什么？`
- `Blueprint 变量类型有哪些？`
- `Low Level Tests 是什么？`
- `CQTest 怎么写测试？`

## 已知限制

- 当前知识库以英文 UE 文档为主，中文提问有时会弱于英文术语提问
- 中文问题和英文 UE 术语之间还没有完整的术语映射层
- 当前主线只做了 docs 问答，没有扩展到项目源码和项目资产
- 回答质量仍然依赖当前知识库覆盖范围

## 上传 GitHub 前建议

- 不要把真实 API Key 留在配置文件里
- 确认本地索引目录没有被提交
- 当前本地缓存目录已经写入 [`.gitignore`](.gitignore)
- 如果仓库要公开，建议只保留示例配置，不保留本机私有路径

## License

本仓库当前使用 [MIT License](LICENSE)。
