# DeepSearchAgent

基于 DeepAgents + LangGraph 框架构建的企业级深度搜索与研究智能体系统，旨在提高企业在复杂决策场景下信息收集和数据分析的效率，同时集成了项目代码审查与 Web 自动化测试等可扩展技能。

## 目录

- [系统架构](#系统架构)
- [核心特性](#核心特性)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [详细设计](#详细设计)
- [API 接口](#api-接口)
- [前端界面](#前端界面)
- [配置说明](#配置说明)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          交互层 (Presentation)                       │
│   ┌──────────────┐    WebSocket     ┌──────────────────────────┐    │
│   │  Vue 前端     │ ◄──────────────► │  FastAPI 后端             │    │
│   │  (HTML/CSS/JS)│  全双工实时推送   │  (异步服务 + JWT 认证)     │    │
│   └──────────────┘                  └──────────────────────────┘    │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                    Agent 任务编排层 (Orchestration)                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  main_agent (主智能体 / 项目经理)                              │    │
│  │  - 任务拆解与资源调度                                         │    │
│  │  - 分派子智能体并行/串行执行                                   │    │
│  │  - 汇总子智能体执行结果，输出报告                               │    │
│  │  - Skills 热加载（code-review / browser-use 等）              │    │
│  └──────────┬──────────┬──────────┬────────────────────────────┘    │
│             │          │          │                                  │
│  ┌──────────▼──┐ ┌─────▼─────┐ ┌──▼──────────────┐                │
│  │ 网络搜索助手 │ │ 数据库查询 │ │ 知识库检索助手    │                │
│  │ (百度搜索)   │ │ (MySQL)   │ │ (Chroma + RAGFlow)│                │
│  │ 多轮递进搜索 │ │ Text2SQL  │ │ 本地 + 云端双引擎  │                │
│  └─────────────┘ └───────────┘ └───────────────────┘                │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                         工具层 (Tools)                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ 百度搜索  │ │ MySQL    │ │ 本地RAG   │ │ RAGFlow  │ │ 文件读写  │ │
│  │ API      │ │ SQL执行  │ │ ChromaDB  │ │ SDK      │ │ MD/PDF   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Markdown │ │ PDF转换   │ │ 上下文    │ │ 文件上传  │              │
│  │ 生成     │ │ Word引擎  │ │ 卸载管理  │ │ 解析     │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                         存储层 (Storage)                             │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  CompositeBackend 混合存储策略                                │    │
│  │  - /workspace/*  → StateBackend   (临时存储，线程级)           │    │
│  │  - /memories/*   → StoreBackend   (Redis 持久化，跨线程)       │    │
│  │  - /offload/*    → StoreBackend   (Redis + TTL 自动过期)       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │  Redis         │  │  MongoDB       │  │  ChromaDB            │  │
│  │  - 会话缓存    │  │  - 对话持久化   │  │  - 本地向量知识库     │  │
│  │  - Token黑名单 │  │  - TTL自动清理  │  │  - 文档向量化存储     │  │
│  │  - 上下文卸载  │  │  - 批量写入优化 │  │  - 相似度检索        │  │
│  └────────────────┘  └────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                       基础设施层 (Infrastructure)                     │
│  ┌──────────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │  ContextVars     │  │  异步并发安全    │  │  YAML Prompt 配置  │  │
│  │  协程级会话隔离   │  │  事件循环绑定    │  │  外置化管理         │  │
│  └──────────────────┘  └────────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心特性

### 1. 分布式多智能体协作架构

采用"主智能体统筹 + 多专家子智能体并行协作"的分布式架构。`main_agent` 充当项目经理角色，负责理解用户意图、拆解任务、调度子智能体执行，并汇总结果输出最终报告。三个专家子智能体各司其职：

| 子智能体 | 职责 | 工具 |
|---------|------|------|
| **网络搜索助手** | 广域公开信息检索，支持多轮递进搜索（3~5轮不同角度） | 百度千帆搜索 API |
| **数据库查询助手** | 企业内部结构化数据查询，支持 Text-to-SQL | MySQL（list_tables / get_table_data / execute_sql） |
| **知识库检索助手** | 私有知识库检索，解决内部规章与技术文档查询 | ChromaDB 本地向量库 + RAGFlow 云端知识库 |

### 2. CompositeBackend 混合存储 + 上下文卸载机制

针对长链路任务中 LLM Context Window 溢出的问题，设计了分层的存储与卸载策略：

- **CompositeBackend 路由存储**：基于路径前缀自动路由到不同存储后端
  - `/workspace/*` → `StateBackend`（临时存储，线程级生命周期）
  - `/memories/*` → `StoreBackend`（Redis 持久化，跨线程可访问）
  - `/offload/*` → `StoreBackend`（Redis + TTL 自动过期）
- **ContextOffloadManager 上下文卸载管理器**：自动监控消息历史的 token 数量，超过阈值（默认 70%）时将旧消息卸载到 Redis，保留引用指针，Agent 可通过 `load_offloaded_message` 工具按需恢复完整内容
- 支持三种卸载策略：`oldest_first`（优先卸载最旧）、`largest_first`（优先卸载最大）、`tool_results_first`（优先卸载工具结果）

### 3. ContextVars 异步会话隔离

使用 Python 3.7+ 的 `ContextVar` 实现协程级会话隔离，确保在 FastAPI 异步并发场景下多用户请求数据不串线。核心上下文变量包括：

- `_session_dir_ctx`：当前会话的工作目录路径
- `_thread_id_ctx`：当前会话的 WebSocket 线程 ID

工具函数可在任意调用深度直接通过 `get_session_context()` / `get_thread_context()` 获取当前上下文，无需层层传参。

### 4. 双层聊天记忆（Redis 缓存 + MongoDB 持久化）

采用 **Redis 缓存 + MongoDB 持久化** 的双层架构：

- **写入路径**：消息先写入内存缓冲区 → 达到阈值或超时后批量刷写到 MongoDB → 同时清除 Redis 缓存
- **读取路径**：优先从 Redis 缓存读取 → 缓存未命中则查询 MongoDB → 查询结果写入 Redis 缓存
- **用户级隔离**：所有数据操作均以 `(user_id, session_id)` 为维度，确保多租户数据安全
- **自动清理**：MongoDB 通过 TTL 索引自动清理 30 天前的过期数据

### 5. WebSocket 实时状态推送

通过 `ToolMonitor` 单例监控类，在工具执行、子智能体调用、任务完成等关键节点向对应会话的前端推送实时状态：

- `tool_start`：工具开始执行
- `assistant_call`：子智能体被调用
- `task_result`：任务执行完成
- `session_created`：工作目录创建

通过 `ContextVar` 获取当前 `thread_id`，实现精准定向推送，避免消息广播到无关会话。

### 6. JWT 双 Token 认证 + Token 黑名单

完整的企业级认证系统：

- **双 Token 机制**：Access Token（30 分钟）+ Refresh Token（7 天），前端自动刷新，用户无感知
- **Token 黑名单**：登出时将 Token 加入 Redis 黑名单（TTL 与原 Token 过期时间一致），防止 Token 被复用
- **多种登录方式**：支持密码登录和邮箱验证码登录
- **安全防护**：账户锁定机制（5 次失败后锁定 30 分钟）、密码强度校验（bcrypt 哈希）

### 7. Skills 可扩展技能系统

支持热加载的技能扩展机制，技能以 `skills/` 目录下的独立模块形式组织，每个 Skill 包含：

- `SKILL.md`：定义技能用途、触发条件和使用方法
- `references/`：详细参考文档
- `scripts/`：辅助脚本

当前内置技能：
- **code-reviewer**：代码审查，检测安全漏洞、性能问题和最佳实践
- **browser-use**：Web 自动化测试，支持浏览器操作、表单填写、截图、数据提取

### 8. 本地知识库 RAG（ChromaDB + 多 Embedding 降级策略）

完全本地运行的知识库检索系统，无需外部依赖：

- **向量存储**：ChromaDB 持久化向量数据库
- **文本分块**：RecursiveCharacterTextSplitter，针对中文优化分隔符
- **多级 Embedding 降级**：DashScope 通义千问 → HuggingFace bge-small-zh-v1.5 → OpenAI 兼容格式，确保在各种网络环境下可用
- **完整工具链**：搜索、状态查询、添加文档、添加文件、清空知识库

### 9. YAML 外置化 Prompt 管理

主智能体和所有子智能体的提示词配置统一外置到 `prompt/prompts.yaml`，支持：

- 热更新提示词，无需修改代码
- 结构化管理：`main_agent` 和 `sub_agents` 分层配置
- 详细的决策规则、优先级规则、工具调用顺序规则等

---

## 技术栈

| 分类 | 技术 | 说明 |
|------|------|------|
| **Agent 框架** | DeepAgents + LangGraph | 核心工厂方法 `create_deep_agent` + 工作流编排 |
| **LLM 服务** | 通义千问 (Qwen) | 通过 OpenAI 兼容接口接入 |
| **后端框架** | FastAPI | 异步 Web 服务 + WebSocket |
| **认证安全** | python-jose + bcrypt + Redis | JWT 双 Token + 密码哈希 + Token 黑名单 |
| **数据库** | MySQL | 业务数据存储 + 用户认证 |
| **缓存** | Redis | 会话缓存 + Token 黑名单 + 上下文卸载 |
| **文档存储** | MongoDB (Motor) | 异步对话历史持久化 |
| **向量数据库** | ChromaDB | 本地知识库向量化存储 |
| **Embedding** | DashScope / HuggingFace / OpenAI | 多级降级的文本向量化 |
| **搜索** | 百度千帆搜索 API | 中文优化的网络搜索 |
| **前端** | HTML + CSS + JavaScript | 原生实现，无构建依赖 |
| **配置管理** | PyYAML + python-dotenv | YAML Prompt + 环境变量 |

---

## 项目结构

```
DeepSearchAgent/
├── api/                          # 后端 API 层
│   ├── server.py                 # FastAPI 主服务 (路由 + WebSocket + 生命周期)
│   ├── auth.py                   # 认证服务 (注册/登录/验证码/登出/刷新Token)
│   ├── middleware.py              # JWT 中间件 (Token 生成/验证/黑名单)
│   ├── models.py                 # Pydantic 数据模型
│   ├── database.py               # MySQL 连接与初始化
│   ├── redis_client.py           # Redis 单例客户端
│   ├── mongodb_client.py         # MongoDB 异步客户端 (连接池 + 索引)
│   ├── context.py                # ContextVars 会话隔离
│   ├── monitor.py                # 工具执行监控 (WebSocket 推送)
│   ├── email_service.py          # 邮件发送服务
│   └── logger.py                 # Agent 执行日志
├── agent/                        # Agent 编排层
│   ├── main_agent.py             # 主智能体 (创建/运行/复合后端)
│   ├── llm.py                    # LLM 模型初始化
│   ├── prompts.py                # Prompt 配置加载
│   └── sub_agents/               # 子智能体
│       ├── network_search_agent.py   # 网络搜索助手
│       ├── database_query_agent.py   # 数据库查询助手
│       ├── knowledge_base_agent.py   # RAGFlow 云端知识库助手
│       └── local_knowledge_base_agent.py  # 本地知识库助手
├── tools/                        # 工具层
│   ├── baidu_search_tools.py     # 百度千帆搜索
│   ├── mysql_tools.py            # MySQL 数据库工具
│   ├── local_rag_tools.py        # 本地向量知识库 (ChromaDB)
│   ├── ragflow_tools.py          # RAGFlow 云端知识库
│   ├── markdown_tools.py         # Markdown 文档生成
│   ├── pdf_tools.py              # Markdown → PDF 转换 (Word COM)
│   ├── upload_file_read_tools.py # 文件内容读取 (MD/DOCX/PDF/XLSX)
│   ├── offload_tools.py          # 上下文卸载管理工具
│   ├── tavily_tools.py           # Tavily 搜索 (备选)
│   └── bing_search_tools.py      # Bing 搜索 (备选)
├── utils/                        # 工具类
│   ├── redis_store_backend.py    # LangGraph Redis Store 后端
│   ├── context_offload_manager.py # 上下文卸载管理器
│   ├── chat_memory_manager.py    # 聊天记忆管理器 (Redis+MongoDB)
│   └── path_utils.py             # 跨平台路径解析
├── prompt/                       # Prompt 配置
│   └── prompts.yaml              # 主智能体 + 子智能体提示词
├── skills/                       # 可扩展技能
│   ├── code-reviewer/            # 代码审查技能
│   │   └── SKILL.md
│   └── browser-use/              # Web 自动化技能
│       ├── SKILL.md
│       └── references/
├── ui/                           # 前端界面
│   ├── index.html                # 主页面
│   ├── auth.html                 # 认证页面
│   ├── css/                      # 样式文件
│   ├── js/                       # 逻辑脚本
│   │   ├── app.js                # 主应用逻辑
│   │   ├── api.js                # API 调用封装
│   │   ├── auth.js               # 认证逻辑
│   │   └── websocket.js          # WebSocket 连接管理
│   └── assets/                   # 静态资源
├── data/                         # 数据目录
│   └── chroma_db/                # ChromaDB 持久化数据
├── sql/                          # 数据库脚本
│   └── company_data.sql          # 业务数据表结构
├── updated/                      # 输出目录 (会话文件)
├── tests/                        # 测试
│   └── test_chat_memory.py
├── requirements.txt              # 依赖清单
└── .env                          # 环境变量配置
```

---

## 快速开始

### 环境准备

1. **Python 3.10+**
2. **MySQL 8.0+**（业务数据库 + 认证系统）
3. **Redis 7.0+**（缓存 + Token 黑名单 + 上下文卸载）
4. **MongoDB 6.0+**（对话历史持久化）

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd DeepSearchAgent

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入实际配置（详见下方配置说明）

# 4. 初始化 MySQL 数据库
mysql -u root -p < sql/company_data.sql

# 5. 启动服务
python api/server.py
```

服务启动后访问 `http://127.0.0.1:8000` 即可使用。

---

## 详细设计

### Agent 执行流程

```
用户请求 → FastAPI /api/task
    │
    ├── 创建会话目录 (updated/session_{thread_id}/output/)
    ├── 设置 ContextVar (session_dir, thread_id)
    ├── 加载历史对话上下文 (Redis → MongoDB)
    │
    ├── main_agent.ainvoke()
    │   ├── 理解用户意图
    │   ├── 判断问题类型 → 选择子智能体
    │   │   ├── 内部事务 → 知识库助手 (local_rag)
    │   │   ├── 外部信息 → 网络搜索助手 (baidu)
    │   │   └── 业务数据 → 数据库查询助手 (db)
    │   ├── 调度子智能体执行（串行/并行）
    │   ├── 汇总执行结果
    │   └── 生成最终输出 (Markdown / PDF)
    │
    ├── 保存 AI 回复到记忆 (缓冲区 → MongoDB)
    ├── 推送任务结果到前端 (WebSocket)
    └── 清理 ContextVar
```

### CompositeBackend 路由规则

```python
def create_composite_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),       # 默认：临时存储
        routes={
            "/memories/": StoreBackend(runtime),  # 记忆路径：Redis 持久化
            "/offload/":  StoreBackend(runtime),  # 卸载路径：Redis + TTL
        }
    )
```

### 上下文卸载流程

```
消息历史 token 数 > 阈值 (70%)
    │
    ├── 选择卸载候选消息（按策略排序）
    ├── 将完整内容写入 Redis Store
    ├── 在原位置替换为轻量引用指针 [OFFLOADED TO REDIS]
    ├── 释放至目标水位 (50%)
    └── Agent 需要时通过 load_offloaded_message 恢复
```

### 聊天记忆读写路径

```
写入: save_message()
    → 内存缓冲区 (按 user_id:session_id 分组)
    → 达到阈值或超时 → 批量刷写 MongoDB
    → 清除 Redis 缓存

读取: get_messages()
    → Redis 缓存命中? → 直接返回
    → 未命中 → 查询 MongoDB
    → 写入 Redis 缓存 (TTL 300s)
    → 返回结果
```

---

## API 接口

### Agent 任务

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/task` | 提交 Agent 任务 | JWT |
| WebSocket | `/ws/{thread_id}` | 实时状态推送 | - |

### 文件操作

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/upload` | 上传文件 | - |
| GET | `/api/download` | 下载文件 | - |
| GET | `/api/files` | 列出文件 | - |

### 认证系统

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 密码登录 |
| POST | `/api/auth/login/code` | 验证码登录 |
| POST | `/api/auth/send-code` | 发送验证码 |
| POST | `/api/auth/refresh` | 刷新 Access Token |
| POST | `/api/auth/logout` | 登出 (Token 加入黑名单) |
| GET | `/api/auth/me` | 获取当前用户信息 |

### 记忆管理

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/memory/stats` | 获取会话记忆统计 | JWT |
| POST | `/api/memory/clear` | 清空会话记忆 | JWT |
| POST | `/api/memory/cleanup` | 清理过期记忆 | - |

---

## 前端界面

前端采用纯 HTML + CSS + JavaScript 实现，无构建依赖，主要包含：

- **认证页面** (`auth.html`)：支持密码登录和验证码登录
- **主页面** (`index.html`)：对话交互界面，实时显示 Agent 执行状态
- **WebSocket 连接管理**：自动重连、心跳保活、连接状态指示器
- **文件管理**：上传文件、浏览输出文件、下载生成的报告

---

## 配置说明

所有配置通过项目根目录的 `.env` 文件管理，主要配置项如下：

### LLM 配置

```env
LLM_QWEN_MAX=qwen-max              # 通义千问模型名称
OPENAI_API_KEY=sk-xxx               # API Key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  # API 地址
LLM_TEXT_EMBEDDING=text-embedding-v4 # Embedding 模型
```

### 百度搜索配置

```env
BAIDU_API_KEY=xxx                   # 百度千帆 API Key
BAIDU_SECRET_KEY=xxx                # 百度千帆 Secret Key
BAIDU_SEARCH_HOST=https://qianfan.baidubce.com/v2/ai_search/web_search
```

### MySQL 配置

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=xxx
MYSQL_DATABASE=pharma_db
```

### Redis 配置

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=xxx                  # 可选
REDIS_DB=0
```

### MongoDB 配置

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=chat_memory_db
MONGODB_CHAT_COLLECTION=deepsearch_agent
MONGODB_MEMORY_TTL_DAYS=30          # 对话历史保留天数
```

### JWT 认证配置

```env
JWT_SECRET_KEY=xxx                  # JWT 签名密钥 (生产环境务必修改)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080  # 7天
```

### RAGFlow 配置 (可选)

```env
RAGFLOW_API_KEY=xxx                 # RAGFlow API Key
RAGFLOW_API_URL=http://localhost:9380  # RAGFlow 服务地址
```