用途：Claude Code 启动时自动读取并注入会话上下文，统一项目认知，减少重复背景描述。
存放位置：项目根目录，与 README.md、.git 同级。
## 一、项目概述
- 项目名称：DeepSearchAgent
- 项目定位：
- 核心能力：根据给定课题开展深度搜索和研究，自动化完成联网搜索、数据库查询、私有知识库检索多源数据汇总和整理，最后输出pdf/md格式报告文档
- 运行环境：Windows 本地开发，生产部署为 Linux
## 二、技术架构
- 前端：HTML+CSS+Vue
- 后端服务：FastAPI+DeepAgents+WebSocket
- 数据库：SQLite 
## 三、项目目录结构
```text
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
## 四、排查和修复bug流程
- 先完整读取log目录下trace日志，还原本次请求从进入Agent到输出结果的完整执行链路，标注每一个节点的输入输出
- 顺着执行链路追溯对应代码，定位根因:从接口层→Agent入口→意图识别→工具调用→结果回填→Prompt组装→LLM生成，逐层排查
- 直接修复对应代码
- 最后输出根因说明、修复的文件与代码片段、修复逻辑解释、本地验证建议
## 五、常见陷阱

## 六、约束
- 保持代码风格与现有项目一致
- 修复bug时不破坏Agent原有主流程与其他工具的能力，不做无关重构


