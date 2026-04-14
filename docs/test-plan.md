# DeepSearchAgent 企业决策支持系统 — 测试方案

> 版本: v1.0
> 编写日期: 2026-04-14
> 项目: DeepSearchAgent (沃华医药企业决策支持系统)

---

## 目录

- [1. 项目概述与测试策略](#1-项目概述与测试策略)
- [2. 认证模块测试方案](#2-认证模块测试方案)
- [3. 智能体核心模块测试方案](#3-智能体核心模块测试方案)
- [4. 会话记忆模块测试方案](#4-会话记忆模块测试方案)
- [5. 文件管理模块测试方案](#5-文件管理模块测试方案)
- [6. 实时通信模块测试方案](#6-实时通信模块测试方案)
- [7. 邮件服务模块测试方案](#7-邮件服务模块测试方案)
- [8. 前端测试方案](#8-前端测试方案)
- [9. 性能测试方案](#9-性能测试方案)
- [10. 安全测试方案](#10-安全测试方案)
- [11. 自动化测试需求与CI/CD方案](#11-自动化测试需求与cicd方案)

---

## 1. 项目概述与测试策略

### 1.1 项目架构总览

```
DeepSearchAgent
├── api/                     # 后端 API 层 (FastAPI)
│   ├── server.py            # 主服务入口, API路由定义
│   ├── auth.py              # 认证服务 (注册/登录/验证码/JWT)
│   ├── middleware.py         # JWT中间件, Token黑名单
│   ├── models.py            # Pydantic数据模型
│   ├── database.py          # MySQL连接与操作
│   ├── mongodb_client.py    # MongoDB客户端 (会话记忆)
│   ├── redis_client.py      # Redis客户端 (缓存/黑名单)
│   ├── email_service.py     # 邮件发送服务
│   ├── monitor.py           # 工具监控 (WebSocket推送)
│   └── context.py           # 上下文管理
├── agent/                   # 智能体层
│   ├── main_agent.py        # 主智能体 (Orchestrator)
│   ├── llm.py               # LLM模型配置
│   ├── prompts.py           # Prompt模板
│   └── sub_agents/          # 子智能体
│       ├── local_knowledge_base_agent.py  # 本地知识库助手 (RAG)
│       ├── database_query_agent.py        # 数据库查询助手
│       └── network_search_agent.py        # 网络搜索助手
├── tools/                   # 工具层
│   ├── mysql_tools.py       # MySQL查询工具
│   ├── baidu_search_tools.py # 百度搜索工具
│   ├── local_rag_tools.py   # 本地RAG工具 (Chroma向量库)
│   ├── markdown_tools.py    # Markdown生成工具
│   ├── pdf_tools.py         # PDF转换工具
│   ├── upload_file_read_tools.py  # 文件读取工具
│   └── offload_tools.py     # 上下文卸载工具
├── utils/                   # 工具类
│   ├── chat_memory_manager.py  # 聊天记忆管理器
│   ├── redis_store_backend.py  # Redis存储后端
│   └── context_offload_manager.py  # 上下文卸载管理
├── ui/                      # 前端 (原生JS + HTML + CSS)
│   ├── auth.html            # 认证页面
│   ├── index.html           # 主页面
│   └── js/
│       ├── app.js           # 主应用逻辑
│       ├── auth.js          # 认证逻辑
│       ├── api.js           # API调用封装
│       └── websocket.js     # WebSocket管理
├── skills/                  # Skills目录 (代码审查等)
├── sql/                     # 数据库初始化SQL
└── data/                    # 数据目录 (Chroma向量库)
```

### 1.2 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| AI框架 | LangChain + deepagents |
| 关系数据库 | MySQL (PyMySQL / mysql-connector) |
| 文档数据库 | MongoDB (Motor异步驱动) |
| 缓存 | Redis |
| 向量数据库 | Chroma |
| 认证 | JWT (python-jose + bcrypt) |
| 邮件 | SMTP (smtplib) |
| 前端 | 原生 JavaScript + HTML + CSS |
| 实时通信 | WebSocket |

### 1.3 核心业务流程

```
用户注册/登录 → 获取JWT Token → 创建搜索任务
    → 主智能体编排 → 子智能体调用(知识库/数据库/网络搜索)
    → 工具执行 → 结果生成(Markdown/PDF)
    → WebSocket实时推送进度 → 展示结果
    → 对话记忆持久化(MongoDB+Redis)
```

### 1.4 测试策略

| 测试类型 | 优先级 | 覆盖范围 | 执行策略 |
|---------|--------|---------|---------|
| 功能测试 | P0 | 全部业务模块 | 手动+自动化 |
| 接口测试 | P0 | 全部API端点 | 自动化 |
| 安全测试 | P0 | 认证/授权/注入/XSS | 手动+自动化 |
| 性能测试 | P1 | API/Agent/并发 | 自动化 |
| 兼容性测试 | P1 | 前端浏览器 | 手动 |
| 可靠性测试 | P2 | 服务降级/故障恢复 | 手动 |

### 1.5 测试环境

| 环境 | 用途 | 配置 |
|------|------|------|
| DEV | 开发自测 | 本地开发机 |
| SIT | 系统集成测试 | 独立测试服务器, 独立DB |
| UAT | 用户验收测试 | 预生产配置 |
| PROD | 生产环境 | 生产配置 |

---

## 2. 认证模块测试方案

> 涉及文件: `api/auth.py`, `api/middleware.py`, `api/models.py`

### 2.1 功能测试

#### 2.1.1 用户注册 (POST /api/auth/register)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-REG-001 | 正常注册-全部字段 | 无 | 提交email/password/name/department/phone/employee_id | 返回code=200, "注册成功", 数据库新增记录 | P0 |
| AUTH-REG-002 | 正常注册-仅必填字段 | 无 | 仅提交email+password | 返回code=200, 其他字段为null | P0 |
| AUTH-REG-003 | 重复邮箱注册 | 已注册邮箱 | 提交已存在的email | 返回code=400, "该邮箱已被注册" | P0 |
| AUTH-REG-004 | 密码过短 | 无 | password长度<6 | Pydantic校验失败, 返回422 | P0 |
| AUTH-REG-005 | 密码过长 | 无 | password长度>50 | Pydantic校验失败, 返回422 | P1 |
| AUTH-REG-006 | 密码纯数字 | 无 | password="123456" | 返回code=400, "密码必须包含数字和字母" | P0 |
| AUTH-REG-007 | 密码纯字母 | 无 | password="abcdef" | 返回code=400, "密码必须包含数字和字母" | P0 |
| AUTH-REG-008 | 邮箱格式非法 | 无 | email="not-an-email" | Pydantic校验失败, 返回422 | P0 |
| AUTH-REG-009 | 手机号含非数字 | 无 | phone="138abc1234" | 返回422校验错误 | P1 |
| AUTH-REG-010 | 空请求体 | 无 | 提交空body | 返回422校验错误 | P1 |
| AUTH-REG-011 | 已删除邮箱重新注册 | 存在status=deleted的邮箱 | 提交该邮箱注册 | 返回code=400, "该邮箱已被注册" | P1 |
| AUTH-REG-012 | 密码含特殊字符 | 无 | password="test@123" | 注册成功, 特殊字符不影响bcrypt | P1 |

#### 2.1.2 密码登录 (POST /api/auth/login)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-LOGIN-001 | 正常登录 | 已注册用户 | 提交正确email+password | 返回code=200, access_token/refresh_token/user_info | P0 |
| AUTH-LOGIN-002 | 错误密码 | 已注册用户 | 提交错误密码 | 返回code=400, "密码错误, 还剩X次机会" | P0 |
| AUTH-LOGIN-003 | 不存在的邮箱 | 无 | 提交未注册email | 返回code=400, "邮箱或密码错误" | P0 |
| AUTH-LOGIN-004 | 账户已锁定 | 用户failed_login_count>=5 | 提交正确凭据 | 返回code=400, "账户已锁定" | P0 |
| AUTH-LOGIN-005 | 账户已禁用 | 用户status=disabled | 提交正确凭据 | 返回code=400, "该账户已被禁用" | P0 |
| AUTH-LOGIN-006 | 账户已删除 | 用户status=deleted | 提交正确凭据 | 返回code=400, "该账户已被删除" | P0 |
| AUTH-LOGIN-007 | 连续5次错误锁定 | 已注册用户 | 连续提交5次错误密码 | 第5次返回"账户即将被锁定", 之后status变为locked | P0 |
| AUTH-LOGIN-008 | 锁定自动解锁 | 账户已锁定30分钟 | 等待lock_until过期后登录 | 登录成功 | P1 |
| AUTH-LOGIN-009 | 登录成功重置失败计数 | 失败次数>0 | 正确密码登录 | failed_login_count重置为0 | P1 |
| AUTH-LOGIN-010 | Token结构验证 | 正常登录 | 解析返回的JWT | 包含sub(email)/exp/iat字段 | P0 |

#### 2.1.3 验证码登录 (POST /api/auth/login/code)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-CODE-001 | 正常验证码登录 | 已发送验证码 | 提交正确email+code | 返回code=200, token | P0 |
| AUTH-CODE-002 | 错误验证码 | 已发送验证码 | 提交错误code | 返回code=400, "验证码错误" | P0 |
| AUTH-CODE-003 | 验证码过期 | 验证码已发送>5分钟 | 提交过期code | 返回code=400, "验证码已过期" | P0 |
| AUTH-CODE-004 | 验证码错误5次 | 已发送验证码 | 连续5次错误验证码 | 返回"验证码错误次数过多" | P0 |
| AUTH-CODE-005 | 未注册邮箱 | 无 | 提交未注册email+code | 返回code=400, "邮箱未注册" | P0 |
| AUTH-CODE-006 | 账户状态异常 | 用户status!=active | 提交验证码 | 返回code=400, "账户状态异常" | P1 |

#### 2.1.4 发送验证码 (POST /api/auth/send-code)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-SEND-001 | 正常发送 | 已注册邮箱 | 请求发送验证码 | 返回code=200, 含verification_code | P0 |
| AUTH-SEND-002 | 未注册邮箱 | 无 | 请求发送验证码 | 返回code=400, "该邮箱未注册" | P0 |
| AUTH-SEND-003 | 频率限制 | 1分钟内已发送 | 再次请求 | 返回code=400, "验证码发送过于频繁" | P0 |
| AUTH-SEND-004 | 错误次数过多 | 验证码错误>=5次 | 请求发送 | 返回code=400, "验证码错误次数过多" | P1 |

#### 2.1.5 获取用户信息 (GET /api/auth/me)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-ME-001 | 正常获取 | 已登录 | 携带有效token请求 | 返回完整UserInfo | P0 |
| AUTH-ME-002 | 无Token | 无 | 不携带Authorization请求 | 返回401 | P0 |
| AUTH-ME-003 | 过期Token | Token已过期 | 携带过期token请求 | 返回401, "认证凭证已过期" | P0 |
| AUTH-ME-004 | 无效Token | 无 | 携带伪造token请求 | 返回401, "无效的认证凭证" | P0 |

#### 2.1.6 登出 (POST /api/auth/logout)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-LOGOUT-001 | 正常登出 | 已登录 | 携带token请求登出 | 返回code=200, Token加入Redis黑名单 | P0 |
| AUTH-LOGOUT-002 | 登出后Token失效 | 已登出 | 使用已登出的token请求 | 返回401, "Token已失效" | P0 |
| AUTH-LOGOUT-003 | Redis不可用 | Redis服务停止 | 请求登出 | 记录警告日志, 不阻止请求 | P1 |

#### 2.1.7 刷新Token (POST /api/auth/refresh)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AUTH-REFRESH-001 | 正常刷新 | 携带有效refresh_token | 请求刷新 | 返回新access_token | P0 |
| AUTH-REFRESH-002 | 使用access_token刷新 | 携带access_token | 请求刷新 | 返回401, "无效的refresh token" | P0 |
| AUTH-REFRESH-003 | 过期refresh_token | refresh_token已过期 | 请求刷新 | 返回401 | P1 |
| AUTH-REFRESH-004 | 黑名单中的refresh_token | 已登出 | 请求刷新 | 返回401 | P1 |

### 2.2 安全测试

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| AUTH-SEC-001 | SQL注入-登录 | email字段注入 `' OR 1=1 --` | 不被注入, 返回正常错误 | P0 |
| AUTH-SEC-002 | SQL注入-注册 | 各字段注入SQL | Pydantic校验拦截 | P0 |
| AUTH-SEC-003 | 暴力破解防护 | 快速发送大量登录请求 | 连续5次失败后锁定 | P0 |
| AUTH-SEC-004 | Token篡改 | 修改JWT payload后请求 | 签名校验失败, 返回401 | P0 |
| AUTH-SEC-005 | 密码明文存储验证 | 检查数据库 | password_hash为bcrypt格式 | P0 |
| AUTH-SEC-006 | 验证码可预测性 | 连续获取验证码分析 | 验证码使用secrets生成, 不可预测 | P1 |

### 2.3 接口自动化测试用例 (pytest)

```python
# tests/api/test_auth.py - 示例结构
import pytest
from httpx import AsyncClient

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "test123",
            "name": "测试用户"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    async def test_register_duplicate_email(self, client: AsyncClient):
        # ... 重复邮箱测试
        pass

class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        # ... 正常登录
        pass

    async def test_login_wrong_password(self, client: AsyncClient):
        # ... 错误密码
        pass
```

---

## 3. 智能体核心模块测试方案

> 涉及文件: `agent/main_agent.py`, `agent/sub_agents/*`, `tools/*`

### 3.1 功能测试

#### 3.1.1 主智能体任务调度 (POST /api/task)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| AGENT-TASK-001 | 正常提交任务 | 已登录 | POST /api/task 含query | 返回status=started, thread_id | P0 |
| AGENT-TASK-002 | 空query | 已登录 | 提交query="" | Pydantic校验失败 | P0 |
| AGENT-TASK-003 | 未认证提交 | 未登录 | 不携带token提交任务 | 返回401 | P0 |
| AGENT-TASK-004 | 指定thread_id | 已登录 | 提交含thread_id的任务 | 使用指定thread_id | P1 |
| AGENT-TASK-005 | 自动生成thread_id | 已登录 | 不指定thread_id | 自动生成UUID作为thread_id | P1 |
| AGENT-TASK-006 | 用户隔离 | 两个用户 | 不同用户提交相同query | 各自独立的thread和结果 | P0 |

#### 3.1.2 本地知识库子智能体 (local_knowledge_base_agent)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| KB-001 | 搜索知识库 | 知识库有数据 | 调用search_knowledge_base(query="xxx") | 返回相关文档片段及相似度 | P0 |
| KB-002 | 知识库为空搜索 | 知识库无数据 | 搜索任意query | 返回"知识库中没有找到相关内容" | P0 |
| KB-003 | 添加文本文档 | 无 | 调用add_documents_to_kb | 返回"成功添加X个文档" | P0 |
| KB-004 | 添加文件到知识库 | 已上传文件 | 调用add_file_to_kb(file_path) | 文件内容被分块向量化 | P0 |
| KB-005 | 添加不存在的文件 | 无 | 传入不存在的file_path | 返回"错误：文件不存在" | P0 |
| KB-006 | 添加不支持的格式 | 无 | 传入.exe文件 | 返回"不支持的文件格式" | P1 |
| KB-007 | 获取知识库状态 | 知识库有数据 | 调用get_kb_status | 返回文档向量块数量 | P1 |
| KB-008 | 清空知识库-确认 | 无 | confirm="yes" | 知识库被清空 | P0 |
| KB-009 | 清空知识库-取消 | 无 | confirm!="yes" | 返回"操作已取消" | P0 |
| KB-010 | PDF文件解析 | 上传PDF文件 | 添加PDF到知识库 | PDF文本被正确提取和分块 | P1 |
| KB-011 | 列出会话文件 | 已上传文件 | 调用list_session_files | 返回文件列表及大小 | P1 |
| KB-012 | 相对路径解析 | 已上传文件 | 使用相对文件名 | 正确解析到会话目录 | P0 |
| KB-013 | 绝对路径解析 | 无 | 使用绝对路径 | 正确读取文件 | P0 |

#### 3.1.3 数据库查询子智能体 (database_query_agent)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| DB-001 | 列出数据库表 | 数据库有表 | 调用list_sql_tables | 返回"可用数据表：table1, table2..." | P0 |
| DB-002 | 读取表数据 | 表有数据 | 调用get_table_data(table_name) | 返回CSV格式前100行 | P0 |
| DB-003 | 读取不存在的表 | 无 | 传入不存在的table_name | 返回错误信息 | P0 |
| DB-004 | 执行SELECT查询 | 表有数据 | execute_sql_query("SELECT * FROM table LIMIT 10") | 返回CSV格式结果 | P0 |
| DB-005 | 执行DML语句 | 无 | execute_sql_query("INSERT INTO ...") | 返回"受影响行数" | P1 |
| DB-006 | SQL注入防护 | 无 | 传入恶意SQL | 表名清洗机制防护 | P0 |
| DB-007 | 数据库配置缺失 | 未配置DB | 调用任何工具 | 返回"数据库配置缺失" | P1 |
| DB-008 | 空数据库 | 数据库无表 | list_sql_tables | 返回"数据库中未找到任何数据表" | P1 |

#### 3.1.4 网络搜索子智能体 (network_search_agent)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| NET-001 | 正常搜索 | API Key已配置 | internet_search("2026年AI趋势") | 返回搜索结果 | P0 |
| NET-002 | API Key未配置 | 未配置BAIDU_API_KEY | 执行搜索 | 返回"百度 API 未初始化" | P0 |
| NET-003 | 搜索超时 | 网络异常 | 搜索query | 返回"百度搜索请求超时" | P1 |
| NET-004 | 连接失败 | 网络不通 | 搜索query | 返回"百度搜索连接失败" | P1 |
| NET-005 | 空查询 | 无 | 搜索空字符串 | 由LLM决定是否调用 | P2 |
| NET-006 | 结果格式解析 | 正常搜索 | 验证result/choices字段解析 | 正确提取搜索内容 | P0 |

#### 3.1.5 工具层测试

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TOOL-MD-001 | Markdown生成 | 无 | 调用generate_markdown | 生成.md文件到output目录 | P1 |
| TOOL-PDF-001 | PDF转换 | 已有.md文件 | 调用convert_md_to_pdf | 生成.pdf文件 | P1 |
| TOOL-FILE-001 | 读取上传文件 | 已上传文件 | 调用read_file_content | 返回文件内容 | P1 |
| TOOL-OFFLOAD-001 | 上下文卸载 | 长对话 | 调用offload相关工具 | 中间结果正确卸载到Redis | P2 |
| TOOL-OFFLOAD-002 | 卸载内容加载 | 已卸载内容 | load_offloaded_message | 正确恢复卸载内容 | P2 |

### 3.2 集成测试

| 用例ID | 测试场景 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| INTEG-001 | 端到端-知识库查询 | 上传文件→添加到知识库→搜索→返回结果 | 完整链路正常 | P0 |
| INTEG-002 | 端到端-数据库查询 | 提问→路由到DB Agent→查询→返回 | 完整链路正常 | P0 |
| INTEG-003 | 端到端-网络搜索 | 提问→路由到搜索Agent→搜索→返回 | 完整链路正常 | P0 |
| INTEG-004 | 多轮对话 | 同一session连续提问 | 历史上下文正确传递 | P0 |
| INTEG-005 | 跨会话隔离 | 两个session各自对话 | 互不干扰 | P0 |
| INTEG-006 | Agent路由准确性 | 不同类型问题 | 正确路由到对应子智能体 | P0 |
| INTEG-007 | 工具链组合 | 复杂问题需要多工具 | 正确编排工具调用 | P1 |

---

## 4. 会话记忆模块测试方案

> 涉及文件: `utils/chat_memory_manager.py`, `api/mongodb_client.py`

### 4.1 功能测试

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| MEM-001 | 保存单条消息 | 无 | save_message(immediate=True) | MongoDB新增1条记录 | P0 |
| MEM-002 | 批量保存消息 | 无 | save_message(immediate=False)×10 | 缓冲区达到阈值后批量写入 | P0 |
| MEM-003 | 获取历史消息 | 已有消息 | get_messages(session_id, user_id) | 返回按时间正序的消息列表 | P0 |
| MEM-004 | Redis缓存命中 | 缓存未过期 | get_messages(use_cache=True) | 从Redis缓存读取 | P0 |
| MEM-005 | Redis缓存失效 | 缓存已过期 | get_messages | 从MongoDB读取并刷新缓存 | P1 |
| MEM-006 | 用户级数据隔离 | 两个用户 | 各自保存消息 | 只能查到自己的消息 | P0 |
| MEM-007 | 清空会话记忆 | 已有消息 | clear_session | 该会话消息全部删除 | P0 |
| MEM-008 | 获取会话统计 | 已有消息 | get_session_stats | 返回total_messages/first_message/last_message | P1 |
| MEM-009 | 手动清理过期数据 | 存在>30天数据 | cleanup_old_sessions(30) | 返回删除数量 | P1 |
| MEM-010 | 最大消息数限制 | 消息数>=1000 | 继续保存 | 最早消息被删除 | P2 |
| MEM-011 | 获取最近上下文 | 已有消息 | get_recent_context(max_messages=20) | 返回最近20条LangChain格式消息 | P0 |
| MEM-012 | flush_all | 缓冲区有数据 | 应用shutdown时调用 | 所有缓冲数据写入MongoDB | P0 |

### 4.2 API测试

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| MEM-API-001 | 获取记忆统计 | 已登录 | POST /api/memory/stats | 返回MemoryStatsResponse | P0 |
| MEM-API-002 | 清空会话记忆 | 已登录 | POST /api/memory/clear | 返回code=200 | P0 |
| MEM-API-003 | 手动清理过期 | 已登录 | POST /api/memory/cleanup | 返回deleted_count | P1 |
| MEM-API-004 | 未认证访问 | 未登录 | 请求记忆API | 返回401 | P0 |

### 4.3 可靠性测试

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| MEM-REL-001 | MongoDB不可用 | 停止MongoDB服务 | 保存失败, 记录错误日志, 不崩溃 | P0 |
| MEM-REL-002 | Redis不可用-降级 | 停止Redis服务 | 自动跳过缓存, 直接查MongoDB | P0 |
| MEM-REL-003 | 缓冲区写入失败 | 模拟MongoDB超时 | 消息重新加入缓冲区 | P1 |
| MEM-REL-004 | MongoDB TTL索引 | 数据超过30天 | 自动清理过期数据 | P1 |

---

## 5. 文件管理模块测试方案

> 涉及文件: `api/server.py` (upload/download/files端点)

### 5.1 功能测试

#### 5.1.1 文件上传 (POST /api/upload)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| FILE-UP-001 | 单文件上传 | 无 | 上传1个文件 | 返回status=uploaded, files含文件名 | P0 |
| FILE-UP-002 | 多文件上传 | 无 | 上传3个文件 | 返回3个文件名 | P0 |
| FILE-UP-003 | 大文件上传 | 无 | 上传接近50MB文件 | 上传成功 | P1 |
| FILE-UP-004 | 特殊文件名 | 无 | 上传含中文/空格文件名 | 文件正确保存 | P1 |
| FILE-UP-005 | 不含thread_id | 无 | 不传thread_id | 请求失败 | P1 |
| FILE-UP-006 | 目录自动创建 | 新thread_id | 首次上传到新session | session目录自动创建 | P0 |

#### 5.1.2 文件下载 (GET /api/download)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| FILE-DL-001 | 正常下载-相对路径 | 文件已存在 | path="session_xxx/output/report.pdf" | 返回FileResponse | P0 |
| FILE-DL-002 | 正常下载-绝对路径 | 文件已存在 | path="D:\\...\\updated\\file.pdf" | 返回FileResponse | P0 |
| FILE-DL-003 | 文件不存在 | 无 | path="nonexistent.txt" | 返回{"error": "File not found"} | P0 |
| FILE-DL-004 | 路径遍历攻击 | 无 | path="../../../etc/passwd" | 返回"Access denied" | P0 |
| FILE-DL-005 | 跨目录访问 | 无 | path指向updated外 | 返回"Access denied" | P0 |

#### 5.1.3 文件列表 (GET /api/files)

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| FILE-LIST-001 | 列出目录文件 | 目录有文件 | path="session_xxx" | 返回文件列表含name/size/mtime | P0 |
| FILE-LIST-002 | 空目录 | 空目录 | path="session_empty" | 返回files=[] | P1 |
| FILE-LIST-003 | 路径遍历防护 | 无 | path="../../../" | 返回"Access denied" | P0 |
| FILE-LIST-004 | 排序验证 | 多文件目录 | 列出文件 | 按mtime倒序排列 | P1 |

---

## 6. 实时通信模块测试方案

> 涉及文件: `api/monitor.py`, `api/server.py` (WebSocket端点)

### 6.1 功能测试

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| WS-001 | 正常WebSocket连接 | 服务运行中 | 连接ws://host/ws/{thread_id} | 连接成功建立 | P0 |
| WS-002 | 消息echo | 已连接 | 发送文本消息 | 收到pong响应 | P0 |
| WS-003 | 工具执行进度推送 | 提交任务 | 监听WebSocket消息 | 收到tool_start事件 | P0 |
| WS-004 | 子智能体调用推送 | 提交任务 | 监听WebSocket消息 | 收到assistant_call事件 | P0 |
| WS-005 | 任务结果推送 | 任务完成 | 监听WebSocket消息 | 收到task_result事件 | P0 |
| WS-006 | 会话目录推送 | 任务开始 | 监听WebSocket消息 | 收到session_created事件 | P1 |
| WS-007 | 连接断开 | 已连接 | 关闭浏览器 | 服务端正确清理连接 | P0 |
| WS-008 | 多客户端同thread | 两个标签页 | 同时连接同thread_id | 均能接收消息 | P1 |
| WS-009 | 旧版WebSocket | 旧客户端 | 连接/ws (无thread_id) | 返回"Client outdated"并关闭 | P1 |

### 6.2 可靠性测试

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| WS-REL-001 | 网络断开重连 | 模拟网络中断 | 客户端自动重连 | P0 |
| WS-REL-002 | 服务重启 | 重启FastAPI | 客户端重连后正常 | P1 |
| WS-REL-003 | 大量并发连接 | 100个WebSocket同时连接 | 均正常通信 | P1 |
| WS-REL-004 | 长时间空闲连接 | 连接后不发送消息 | 心跳保活 | P2 |

---

## 7. 邮件服务模块测试方案

> 涉及文件: `api/email_service.py`

### 7.1 功能测试

| 用例ID | 测试场景 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EMAIL-001 | 发送验证码邮件 | SMTP已配置 | send_verification_email(email, code) | 邮件发送成功, 包含验证码 | P0 |
| EMAIL-002 | 发送欢迎邮件 | SMTP已配置 | send_welcome_email(email, name) | 邮件发送成功 | P1 |
| EMAIL-003 | SMTP连接失败 | SMTP配置错误 | 发送邮件 | 返回False, 记录错误日志 | P0 |
| EMAIL-004 | SSL连接 | port=465 | 发送邮件 | 使用SMTP_SSL | P1 |
| EMAIL-005 | TLS连接 | port!=465 | 发送邮件 | 使用SMTP+starttls | P1 |
| EMAIL-006 | 无效收件人 | 无 | 发送到无效邮箱 | SMTP报错, 返回False | P1 |

### 7.2 安全测试

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| EMAIL-SEC-001 | SMTP凭证泄露 | 检查日志和响应 | 不输出SMTP_PASSWORD | P0 |
| EMAIL-SEC-002 | 邮件头注入 | 注入换行符到收件人 | 不执行注入 | P1 |

---

## 8. 前端测试方案

> 涉及文件: `ui/auth.html`, `ui/index.html`, `ui/js/*.js`

### 8.1 认证页面功能测试

| 用例ID | 测试场景 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| UI-AUTH-001 | 登录-正常流程 | 输入邮箱密码→点击登录 | 跳转到主页, localStorage存储token | P0 |
| UI-AUTH-002 | 登录-空字段 | 不输入直接点击 | 显示提示"请输入邮箱/密码" | P0 |
| UI-AUTH-003 | 注册-正常流程 | 切换到注册→填写信息→提交 | 显示"注册成功" | P0 |
| UI-AUTH-004 | 注册-密码强度不足 | 输入弱密码 | 显示错误提示 | P0 |
| UI-AUTH-005 | 验证码登录 | 切换到验证码→发送→输入→登录 | 成功登录 | P0 |
| UI-AUTH-006 | Token过期跳转 | Token过期后操作 | 自动跳转到登录页 | P0 |
| UI-AUTH-007 | 已登录访问登录页 | localStorage有token | 自动跳转到主页 | P1 |

### 8.2 主页面功能测试

| 用例ID | 测试场景 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| UI-MAIN-001 | 提交搜索 | 输入query→点击搜索 | 显示进度→显示结果 | P0 |
| UI-MAIN-002 | Ctrl+Enter快捷键 | 输入query→Ctrl+Enter | 触发搜索 | P1 |
| UI-MAIN-003 | 文件上传-点击 | 点击上传区域→选择文件 | 文件出现在已选列表 | P0 |
| UI-MAIN-004 | 文件上传-拖拽 | 拖拽文件到上传区 | 文件出现在已选列表 | P0 |
| UI-MAIN-005 | 文件大小超限 | 上传>50MB文件 | 显示Toast"超过50MB限制" | P0 |
| UI-MAIN-006 | 文件移除 | 点击文件×按钮 | 文件从列表移除 | P1 |
| UI-MAIN-007 | 清空文件 | 点击清空按钮 | 所有已选文件清除 | P1 |
| UI-MAIN-008 | WebSocket进度展示 | 提交搜索后观察 | 实时显示工具/助手/结果进度 | P0 |
| UI-MAIN-009 | 结果展示-文本 | 搜索完成 | Markdown/文本格式化展示 | P0 |
| UI-MAIN-010 | 结果展示-文件下载链接 | 结果含文件路径 | 显示下载链接 | P0 |
| UI-MAIN-011 | 服务器状态检测 | 服务在线/离线 | 状态指示器显示在线/离线 | P1 |
| UI-MAIN-012 | 重复提交防护 | 搜索中再次点击 | 忽略, 不重复提交 | P0 |

### 8.3 侧边栏功能测试

| 用例ID | 测试场景 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| UI-SIDE-001 | 侧边栏折叠 | 点击折叠按钮 | 侧边栏收起/展开 | P1 |
| UI-SIDE-002 | 页面切换-主页 | 点击主页导航 | 显示主页内容 | P0 |
| UI-SIDE-003 | 页面切换-个人资料 | 点击个人资料 | 显示个人资料页 | P0 |
| UI-SIDE-004 | 退出登录 | 点击退出→确认 | 清除token, 跳转登录页 | P0 |

### 8.4 浏览器兼容性测试

| 浏览器 | 版本 | 测试内容 | 优先级 |
|--------|------|---------|--------|
| Chrome | 最新版 | 全功能 | P0 |
| Edge | 最新版 | 全功能 | P0 |
| Firefox | 最新版 | 全功能 | P1 |
| Safari | 最新版 | 基础功能 | P1 |

---

## 9. 性能测试方案

### 9.1 API性能基准

| 测试场景 | 并发数 | 目标指标 | 可接受阈值 | 优先级 |
|---------|--------|---------|-----------|--------|
| 注册接口 | 50 | 平均响应时间 | < 500ms | P0 |
| 登录接口 | 100 | 平均响应时间 | < 300ms | P0 |
| 验证码发送 | 50 | 平均响应时间 | < 1s (含SMTP) | P1 |
| 获取用户信息 | 200 | 平均响应时间 | < 100ms | P0 |
| 任务提交 | 50 | 平均响应时间 | < 200ms | P0 |
| 文件上传(10MB) | 20 | 平均响应时间 | < 5s | P1 |
| 文件下载(10MB) | 20 | 平均响应时间 | < 3s | P1 |
| 记忆统计查询 | 100 | 平均响应时间 | < 200ms | P1 |

### 9.2 智能体性能测试

| 测试场景 | 测试指标 | 可接受阈值 | 优先级 |
|---------|---------|-----------|--------|
| 简单问答(无需工具) | 首次响应时间 | < 10s | P0 |
| 知识库查询 | 端到端响应时间 | < 30s | P0 |
| 数据库查询 | 端到端响应时间 | < 30s | P0 |
| 网络搜索 | 端到端响应时间 | < 45s | P0 |
| 复杂多步推理 | 端到端响应时间 | < 120s | P1 |
| 向量检索延迟 | 单次检索时间 | < 2s | P1 |

### 9.3 并发与压力测试

| 测试场景 | 并发数 | 持续时间 | 目标 | 优先级 |
|---------|--------|---------|------|--------|
| 混合API压力 | 200 | 5min | 错误率<1%, P99<3s | P0 |
| WebSocket并发 | 100 | 5min | 连接稳定, 消息不丢失 | P1 |
| 文件上传并发 | 30 | 5min | 不出现文件损坏 | P1 |
| 记忆写入并发 | 50 | 5min | 数据不丢失 | P1 |

### 9.4 资源使用测试

| 测试指标 | 监控方式 | 告警阈值 | 优先级 |
|---------|---------|---------|--------|
| CPU使用率 | 系统监控 | > 80% | P0 |
| 内存使用率 | 系统监控 | > 80% | P0 |
| MySQL连接数 | DB监控 | > 配置上限80% | P0 |
| MongoDB连接数 | DB监控 | > 配置上限80% | P1 |
| Redis内存 | Redis监控 | > maxmemory 80% | P1 |
| 磁盘IO | 系统监控 | 持续> 80% | P1 |

### 9.5 推荐性能测试工具

| 工具 | 用途 | 优先级 |
|------|------|--------|
| Locust | API压力测试 | P0 |
| k6 | API性能基准 | P1 |
| Artillery | WebSocket压力测试 | P1 |
| Py-Spy | Python性能分析 | P2 |

---

## 10. 安全测试方案

### 10.1 OWASP Top 10 覆盖

| 风险类别 | 本项目相关点 | 测试方法 | 预期结果 | 优先级 |
|---------|-------------|---------|---------|--------|
| A01-权限控制失效 | JWT认证/用户隔离 | 使用A用户token访问B用户数据 | 返回401/403 | P0 |
| A02-加密机制失败 | 密码存储/Token签名 | 检查密码哈希方式/JWT算法 | bcrypt+HS256 | P0 |
| A03-注入 | SQL注入/路径遍历 | 在各输入点注入恶意内容 | 被防护或校验拦截 | P0 |
| A04-不安全设计 | 验证码逻辑/账户锁定 | 分析业务逻辑漏洞 | 安全机制有效 | P0 |
| A05-安全配置错误 | CORS/Debug模式/默认密钥 | 检查生产环境配置 | CORS限制/无debug/密钥更新 | P0 |
| A06-过时组件 | 依赖库版本 | 扫描pip依赖 | 无已知高危漏洞 | P1 |
| A07-身份认证失败 | 暴力破解/会话管理 | 自动化攻击测试 | 防护机制生效 | P0 |
| A08-软件和数据完整性失败 | CI/CD安全 | 检查部署流程 | 依赖锁定/签名验证 | P2 |
| A09-日志监控不足 | 安全事件记录 | 检查日志覆盖 | 关键操作有日志 | P1 |
| A10-SSRF | 搜索API/文件读取 | 构造内网请求 | 不暴露内网信息 | P1 |

### 10.2 关键安全测试用例

#### 10.2.1 SQL注入

| 用例ID | 注入点 | 测试Payload | 预期结果 | 优先级 |
|--------|--------|------------|---------|--------|
| SEC-SQL-001 | 登录邮箱 | `' OR 1=1 --` | 返回正常错误 | P0 |
| SEC-SQL-002 | 注册各字段 | `"; DROP TABLE employee_login_info; --` | 参数化查询防护 | P0 |
| SEC-SQL-003 | execute_sql_query工具 | `DROP TABLE xxx` | **风险点**: Agent可执行DML | P0 |
| SEC-SQL-004 | get_table_data表名 | `users; DROP TABLE orders` | 表名清洗防护 | P0 |

#### 10.2.2 路径遍历

| 用例ID | 注入点 | 测试Payload | 预期结果 | 优先级 |
|--------|--------|------------|---------|--------|
| SEC-PATH-001 | 文件下载path | `../../../etc/passwd` | 返回Access denied | P0 |
| SEC-PATH-002 | 文件列表path | `../../` | 返回Access denied | P0 |
| SEC-PATH-003 | 文件上传filename | `../../../malicious.exe` | 文件名被安全处理 | P0 |
| SEC-PATH-004 | add_file_to_kb路径 | `/etc/shadow` | 受限于实际文件权限 | P1 |

#### 10.2.3 XSS

| 用例ID | 注入点 | 测试Payload | 预期结果 | 优先级 |
|--------|--------|------------|---------|--------|
| SEC-XSS-001 | 搜索结果展示 | `<script>alert(1)</script>` | escapeHtml转义 | P0 |
| SEC-XSS-002 | 文件名展示 | `"><script>alert(1)</script>` | HTML转义 | P0 |
| SEC-XSS-003 | 进度消息 | WebSocket推送恶意HTML | 前端escapeHtml处理 | P1 |

#### 10.2.4 认证与授权

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| SEC-AUTH-001 | 越权访问 | 使用A用户token访问B用户会话记忆 | 数据隔离, 返回空或403 | P0 |
| SEC-AUTH-002 | Token伪造 | 修改JWT的sub字段 | 签名校验失败 | P0 |
| SEC-AUTH-003 | Token重放 | 使用已登出Token请求 | Token在黑名单, 返回401 | P0 |
| SEC-AUTH-004 | 无认证访问 | 不带Token访问/api/task | 返回401 | P0 |
| SEC-AUTH-005 | 管理员权限 | 普通用户尝试管理员操作 | 无管理员功能点, 暂无风险 | P2 |

#### 10.2.5 敏感信息泄露

| 用例ID | 测试场景 | 测试方法 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| SEC-INFO-001 | API文档暴露 | 访问/docs和/redoc | 生产环境应关闭 | P0 |
| SEC-INFO-002 | 错误堆栈泄露 | 触发500错误 | 不返回堆栈信息 | P0 |
| SEC-INFO-003 | 数据库凭证 | 检查.env和日志 | 不明文输出 | P0 |
| SEC-INFO-004 | API Key泄露 | 检查前端代码和日志 | 不暴露BAIDU_API_KEY等 | P0 |
| SEC-INFO-005 | 验证码明文返回 | 调用send-code | **风险点**: 当前测试模式直接返回验证码 | P0 |

### 10.3 安全配置审计

| 审计项 | 当前状态 | 建议修复 | 优先级 |
|--------|---------|---------|--------|
| CORS配置 `allow_origins=["*"]` | 允许所有来源 | 生产环境限制为具体域名 | P0 |
| JWT默认密钥 `your-secret-key-change-this` | 使用硬编码默认值 | 强制从环境变量读取, 启动时校验 | P0 |
| 验证码直接返回 | send-code返回验证码明文 | 生产模式应通过邮件发送 | P0 |
| DEBUG日志 | 搜索工具打印API Key前8位 | 移除敏感信息日志 | P0 |
| 文件上传无类型限制 | 任意文件类型可上传 | 限制白名单文件类型 | P1 |
| 文件上传无大小限制(服务端) | 仅前端50MB限制 | 服务端增加大小校验 | P1 |
| HTTPS | 未强制 | 生产环境强制HTTPS | P0 |

---

## 11. 自动化测试需求与CI/CD方案

### 11.1 自动化测试架构

```
tests/
├── conftest.py                  # 公共fixture (测试客户端/数据库/mock)
├── api/                         # API接口测试
│   ├── test_auth.py             # 认证接口测试
│   ├── test_task.py             # 任务接口测试
│   ├── test_file.py             # 文件管理测试
│   ├── test_memory.py           # 记忆接口测试
│   └── test_middleware.py       # 中间件测试
├── unit/                        # 单元测试
│   ├── test_models.py           # 数据模型测试
│   ├── test_email_service.py    # 邮件服务测试
│   ├── test_chat_memory.py      # 记忆管理器测试
│   └── test_mongodb_client.py   # MongoDB客户端测试
├── agent/                       # 智能体测试
│   ├── test_main_agent.py       # 主智能体测试
│   ├── test_local_rag.py        # 知识库工具测试
│   ├── test_mysql_tools.py      # 数据库工具测试
│   └── test_search_tools.py     # 搜索工具测试
├── integration/                 # 集成测试
│   ├── test_e2e_search.py       # 端到端搜索
│   └── test_e2e_kb.py           # 端到端知识库
├── performance/                 # 性能测试
│   ├── locustfile.py            # Locust性能脚本
│   └── k6_scripts/              # k6测试脚本
├── security/                    # 安全测试
│   ├── test_sql_injection.py    # SQL注入测试
│   ├── test_path_traversal.py   # 路径遍历测试
│   └── test_auth_security.py    # 认证安全测试
└── ui/                          # 前端测试
    └── e2e/                     # Playwright端到端测试
```

### 11.2 自动化测试技术选型

| 测试层次 | 工具 | 用途 | 优先级 |
|---------|------|------|--------|
| 单元测试 | pytest + pytest-asyncio | 后端逻辑/工具函数 | P0 |
| 接口测试 | pytest + httpx (AsyncClient) | API端点测试 | P0 |
| Mock | pytest-mock + unittest.mock | 外部依赖隔离(LLM/DB/SMTP) | P0 |
| 数据库测试 | pytest fixtures + 测试DB | 真实DB交互测试 | P0 |
| 前端E2E | Playwright | 浏览器自动化测试 | P1 |
| 性能测试 | Locust | API负载测试 | P1 |
| 安全扫描 | bandit + safety | 代码安全扫描+依赖漏洞 | P1 |
| 覆盖率 | pytest-cov | 测试覆盖率统计 | P1 |

### 11.3 核心Fixture设计

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient
from api.server import app

@pytest.fixture
async def client():
    """异步测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def auth_token(client):
    """获取认证Token"""
    response = await client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "test1234"
    })
    data = response.json()
    return data["data"]["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """带认证的请求头"""
    return {"Authorization": f"Bearer {auth_token}"}

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM调用, 避免测试时实际调用API"""
    # ...
    pass

@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis客户端"""
    # ...
    pass

@pytest.fixture
def mock_smtp(monkeypatch):
    """Mock SMTP发送"""
    # ...
    pass
```

### 11.4 CI/CD集成方案

#### 11.4.1 GitHub Actions 工作流

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_root
          MYSQL_DATABASE: test_db
        ports: ["3306:3306"]
      redis:
        image: redis:7
        ports: ["6379:6379"]
      mongodb:
        image: mongo:7
        ports: ["27017:27017"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/unit tests/api -v --cov --cov-report=xml
      - uses: codecov/codecov-action@v4

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit safety
      - run: bandit -r api/ agent/ tools/ utils/ -f json -o bandit-report.json
      - run: safety check --json

  integration-test:
    runs-on: ubuntu-latest
    needs: unit-test
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/integration -v

  performance-test:
    runs-on: ubuntu-latest
    needs: unit-test
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: locust -f tests/performance/locustfile.py --headless -u 50 -r 10 -t 2m
```

#### 11.4.2 测试门禁

| 阶段 | 门禁条件 | 不通过操作 |
|------|---------|-----------|
| PR合并 | 单元测试通过 + 覆盖率>=70% | 阻止合并 |
| PR合并 | 安全扫描无高危漏洞 | 阻止合并 |
| 发版 | 集成测试通过 | 阻止发版 |
| 发版 | 性能测试无严重退化 | 人工评审 |

### 11.5 各模块自动化优先级

| 模块 | 自动化优先级 | 预计用例数 | 说明 |
|------|------------|-----------|------|
| 认证模块 | P0 | ~40 | 核心安全模块, 必须自动化 |
| API接口 | P0 | ~25 | 所有端点需自动化覆盖 |
| 数据模型 | P0 | ~15 | Pydantic校验自动化 |
| 记忆管理 | P1 | ~20 | 依赖MongoDB/Redis |
| 文件管理 | P1 | ~15 | 依赖文件系统 |
| 智能体工具 | P1 | ~30 | 需Mock LLM和外部API |
| 前端E2E | P2 | ~20 | Playwright实现 |
| 性能测试 | P2 | ~10 | Locust脚本 |

### 11.6 Mock策略

| 外部依赖 | Mock方式 | 理由 |
|---------|---------|------|
| LLM API | 录制/回放或预设响应 | 避免API调用成本和不稳定性 |
| 百度搜索API | Mock requests | 避免外部依赖和费用 |
| SMTP | Mock smtplib | 避免发送真实邮件 |
| MySQL | 测试数据库 | 使用独立测试库, 测试后清理 |
| MongoDB | 测试数据库 | 使用独立测试库 |
| Redis | 测试Redis实例 | 使用独立DB号 |
| Chroma向量库 | 临时内存实例 | 使用内存模式, 测试后销毁 |

### 11.7 已识别风险与待办事项

| 风险ID | 风险描述 | 影响等级 | 建议措施 |
|--------|---------|---------|---------|
| RISK-001 | `execute_sql_query`工具无SQL类型限制, Agent可执行DML/DDL | 高 | 限制为只读查询, 或增加SQL关键词白名单 |
| RISK-002 | 验证码接口直接返回明文验证码 | 高 | 生产模式切换为邮件发送, 不返回验证码内容 |
| RISK-003 | CORS允许所有来源 | 高 | 生产环境限制具体域名 |
| RISK-004 | JWT默认密钥硬编码 | 高 | 启动时强制校验环境变量, 无配置则拒绝启动 |
| RISK-005 | 文件上传服务端无大小/类型限制 | 中 | 增加服务端文件大小和类型校验 |
| RISK-006 | Agent日志打印API Key前8位 | 中 | 移除敏感信息日志输出 |
| RISK-007 | Redis不可用时跳过Token黑名单检查 | 中 | 评估是否需要在Redis不可用时拒绝请求 |
| RISK-008 | simple_web_search返回原始HTML | 低 | 此为备用方案, 建议移除或标记为开发专用 |

---

> **文档维护说明**: 本测试方案应随项目迭代持续更新。每个Sprint结束后回顾测试覆盖率, 补充遗漏场景, 关闭已完成用例。