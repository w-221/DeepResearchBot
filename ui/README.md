# DeepSearchAgent 前端项目

## 项目简介

DeepSearchAgent 前端是一个基于 Vue2 构建的现代化 Web 应用，为后端深度搜索服务提供直观、美观的用户界面。

## 技术栈

- **HTML5** - 页面结构
- **CSS3** - 样式设计（使用 CSS 变量）
- **JavaScript (ES6+)** - 交互逻辑
- **Vue 2.6.14** - 前端框架（通过 CDN 引入）

## 项目结构

```
ui/
├── index.html              # 主入口文件
├── css/
│   ├── reset.css          # 样式重置
│   ├── variables.css      # CSS 变量定义
│   └── style.css          # 主样式文件
├── js/
│   ├── api.js             # API 请求封装
│   ├── websocket.js       # WebSocket 连接管理
│   └── app.js             # Vue 应用主文件
└── assets/                # 静态资源目录
```

## 功能特性

### 1. 智能查询
- 支持多行文本输入
- 支持 Ctrl+Enter 快捷提交
- 文件上传功能（支持 .md, .docx, .pdf, .xlsx 格式）

### 2. 实时进度展示
- WebSocket 实时推送任务执行状态
- 工具调用过程可视化
- 事件日志记录

### 3. 结果展示
- 最终结果展示（支持简单 Markdown 格式）
- 生成的文件列表
- 文件下载功能

### 4. 用户体验
- 深色主题设计
- 响应式布局
- Toast 通知提示
- 平滑动画效果

## 启动方式

### 方法一：直接打开（开发测试）

直接用浏览器打开 `index.html` 文件：

```bash
# Windows
start ui/index.html

# 或者手动双击打开
```

### 方法二：使用 Python HTTP 服务器

在项目根目录下运行：

```bash
# Python 3
python -m http.server 8080

# 或指定端口
python -m http.server 3000
```

然后访问：http://localhost:8080/ui/

### 方法三：使用 Node.js http-server

首先安装 http-server：

```bash
npm install -g http-server
```

然后运行：

```bash
cd ui
http-server -p 8080
```

访问：http://localhost:8080

### 方法四：使用 VS Code Live Server 插件

1. 安装 "Live Server" 插件
2. 右键点击 `index.html` 文件
3. 选择 "Open with Live Server"

## 后端服务配置

前端需要后端服务运行在 `http://127.0.0.1:8000`。

如果后端地址不同，请修改以下文件中的配置：

- `js/api.js` - 修改 `API_BASE_URL` 变量
- `js/websocket.js` - 修改 `WS_BASE_URL` 变量

### 启动后端服务

```bash
# 在项目根目录下运行后端服务
python api/server.py
```

## API 接口

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | /api/task | 启动新任务 |
| POST | /api/upload | 上传文件 |
| GET | /api/download | 下载文件 |
| GET | /api/files | 列出文件 |
| WS | /ws/{thread_id} | WebSocket 连接 |

## 浏览器兼容性

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

需要支持：
- ES6+ JavaScript
- CSS Grid
- CSS Variables
- WebSocket
- Fetch API

## 开发建议

1. **修改样式**：编辑 `css/style.css` 或 `css/variables.css`
2. **修改逻辑**：编辑 `js/app.js`
3. **添加新功能**：在对应模块中添加代码
4. **调试**：使用浏览器开发者工具（F12）

## 常见问题

### Q: 无法连接到后端服务？
A: 请确保后端服务已启动，并且运行在正确的端口（默认 8000）。

### Q: 文件上传失败？
A: 检查文件大小和格式是否符合要求，后端可能有限制。

### Q: WebSocket 连接断开？
A: 检查网络连接，后端服务是否正常运行。

### Q: 页面样式显示异常？
A: 确保所有 CSS 文件路径正确，浏览器支持 CSS 变量。

## 许可证

MIT License