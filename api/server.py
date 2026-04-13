import os
import sys
import uuid
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Header, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Dict, Optional
import shutil
from api.mongodb_client import init_mongodb_indexes, close_mongodb_connection
from utils.chat_memory_manager import get_memory_manager
from api.middleware import get_current_user


# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import agent runner and monitor
# 注意：agent.main_agent 导入时会初始化 main_agent，这可能需要几秒钟
from agent.main_agent import run_deep_agent
from api.monitor import monitor

# Import authentication router
from api.auth import auth_router

# Import database initialization
from api.database import initialize_tables, test_connection


# 定义 lifespan 上下文管理器（替代 @app.on_event）
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup 事件
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    print(f"[Server] WebSocket Manager bound to loop: {id(loop)}")
    # 初始化MongoDB索引
    await init_mongodb_indexes()
    print("[Server] MongoDB indexes initialized")
    yield
    # Shutdown 事件
    print("[Server] Application shutting down...")
    # 刷新所有记忆缓冲区
    memory_manager = get_memory_manager()
    await memory_manager.flush_all()

    # 关闭MongoDB连接
    await close_mongodb_connection()
    print("[Server] MongoDB connection closed")
    print("[Server] Application shutdown complete")

# 创建连接管理器对象（在 lifespan 之前定义，以便 lifespan 可以访问）
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        # 延迟绑定 loop，防止初始化时 loop 不一致
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop
        monitor.set_websocket_manager(self)

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        self.active_connections[thread_id] = websocket
        print(f"Client connected: {thread_id}")

    def disconnect(self, websocket: WebSocket, thread_id: str):
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]
        print(f"Client disconnected: {thread_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_to_thread(self, message: dict, thread_id: str):
        if thread_id in self.active_connections:
            websocket = self.active_connections[thread_id]
            await websocket.send_json(message)


# 全局 manager 实例
manager = ConnectionManager()

class MemoryStatsResponse(BaseModel):
    """记忆统计响应"""
    session_id: str
    total_messages: int
    first_message: Optional[str] = None
    last_message: Optional[str] = None


class ClearSessionRequest(BaseModel):
    """清空会话请求"""
    session_id: str

# 使用 lifespan 创建 FastAPI 应用
app = FastAPI(
    title="DeepAgents API",
    description="Deep Agents API with JWT Authentication",
    version="1.0.0",  # 指定应用当前版本号
    lifespan=lifespan,  # 指定应用的生命周期管理器
    # 配置 OpenAPI 安全方案
    openapi_components={
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Bearer Token 认证。请先调用 /api/auth/login 获取 token，格式: Bearer <token>"
            }
        }
    }
)

# 挂载输出目录，以便前端访问生成的静态文件
# 输出目录位于项目根目录下的 updated
output_dir = os.path.join(project_root, "updated")
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
app.mount("/outputs", StaticFiles(directory=output_dir), name="outputs")

# UI 目录路径
ui_dir = os.path.join(project_root, "ui")

# 定义上传目录 updated
updated_dir = os.path.join(project_root, "updated")
if not os.path.exists(updated_dir):
    os.makedirs(updated_dir)

# 配置 CORS（必须在路由定义之前）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含认证路由（必须在静态文件挂载之前）
app.include_router(auth_router)

# 根路由重定向到 auth.html
@app.get("/")
async def root():
    """根路径重定向到认证页面"""
    return FileResponse(os.path.join(ui_dir, "auth.html"))

# UI 路由处理 - 使用路由代替静态文件挂载，避免自动返回 index.html

@app.get("/ui")
async def ui_root():
    """UI路径重定向到认证页面"""
    return FileResponse(os.path.join(ui_dir, "auth.html"))

@app.get("/ui/")
async def ui_root_with_slash():
    """UI路径重定向到认证页面（带斜杠）"""
    return FileResponse(os.path.join(ui_dir, "auth.html"))

@app.get("/ui/auth.html")
async def auth_page():
    """认证页面"""
    return FileResponse(os.path.join(ui_dir, "auth.html"))

@app.get("/ui/index.html")
async def index_page():
    """主页面"""
    return FileResponse(os.path.join(ui_dir, "index.html"))


# 挂载静态资源目录（css, js, assets）到独立的路径 /assets/
# 注意：使用独立路径避免与 /ui/ 路由冲突
if os.path.exists(ui_dir):
    # 挂载 ui 目录到 /assets，然后通过 /assets/ 访问
    # 例如：/assets/css/style.css -> ui/css/style.css
    app.mount("/assets", StaticFiles(directory=ui_dir), name="assets")


class TaskRequest(BaseModel):
    query: str
    thread_id: str | None = None


# /api/task接口：接收用户提示词，启动 Agent 运行
@app.post("/api/task",
          tags=["Agent"],
          summary="接收用户提示词,启动一个新的 Agent 任务")
async def run_task(task_request: TaskRequest, current_user: Dict = Depends(get_current_user)):
    """
    启动一个新的 Agent 任务
    """
    thread_id = task_request.thread_id or str(uuid.uuid4())
    user_id = current_user["sub"]  # 从 token 中提取用户标识（email）

    # 异步运行 Agent，不阻塞主线程
    # 注意：run_deep_agent 现在是异步函数，直接在主事件循环中运行
    # 在生产环境中建议使用 Celery 或其他任务队列
    asyncio.create_task(run_deep_agent(task_request.query, thread_id, user_id))

    return {"status": "started", "thread_id": thread_id}


@app.options("/api/task")
async def run_task_options():
    """处理 OPTIONS 请求（CORS 预检）"""
    return {"status": "ok"}


# 上传文件接口
@app.post("/api/upload",
          tags=["File"],
          summary="用户文件上传接口")
async def upload_files(files: List[UploadFile] = File(...), thread_id: str = Form(...)):
    """
    上传文件到 updated/session_{thread_id} 目录
    """
    target_dir = os.path.join(updated_dir, f"session_{thread_id}")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    saved_files = []
    for file in files:
        file_path = os.path.join(target_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)

    return {"status": "uploaded", "files": saved_files}


# 下载文件接口
@app.get("/api/download",
         tags=["File"],
         summary="文件下载接口")
async def download_file(path: str):
    """
    下载指定文件
    path: 绝对路径或相对于 updated 目录的相对路径
    """
    # 路径解析：如果是相对路径，基于 output_dir（即 updated 目录）解析
    if not os.path.isabs(path):
        abs_path = os.path.abspath(os.path.join(output_dir, path))
    else:
        abs_path = os.path.abspath(path)

    # 安全检查：确保路径在 output_dir（updated 目录）下
    output_abs = os.path.abspath(output_dir)
    try:
        if sys.platform == "win32":
            check_path = os.path.normcase(abs_path)
            check_output = os.path.normcase(output_abs)
        else:
            check_path = abs_path
            check_output = output_abs

        if not check_path.startswith(check_output):
            return {"error": "Access denied: Path must be within updated directory"}
    except Exception as e:
        return {"error": f"Path check failed: {e}"}

    if not os.path.exists(abs_path):
        return {"error": "File not found"}

    return FileResponse(abs_path, filename=os.path.basename(abs_path))


@app.get("/api/files",
         tags=["File"],
         summary="列出指定目录下的文件")
async def list_files(path: str):
    """
    列出指定目录下的文件
    path: 相对于 output 目录的路径
    """
    # 安全检查：确保路径在 output_dir 下
    print(f"[DEBUG] list_files request path: {path}")

    # 如果是相对路径，相对于 output_dir 解析（避免当前工作目录影响）
    if not os.path.isabs(path):
        abs_path = os.path.abspath(os.path.join(output_dir, path))
    else:
        abs_path = os.path.abspath(path)

    output_abs = os.path.abspath(output_dir)
    print(f"[DEBUG] abs_path: {abs_path}")
    print(f"[DEBUG] output_dir abs: {output_abs}")

    # 使用 os.path.commonpath 或转为小写比较来处理 Windows 路径大小写问题
    try:
        # 在 Windows 上，路径大小写可能不一致，使用 normcase 标准化
        if sys.platform == "win32":
            check_path = os.path.normcase(abs_path)
            check_output = os.path.normcase(output_abs)
        else:
            check_path = abs_path
            check_output = output_abs

        if not check_path.startswith(check_output):
            print(f"[ERROR] Access denied. {check_path} not startswith {check_output}")
            return {"error": "Access denied: Path must be within output directory"}
    except Exception as e:
        print(f"[ERROR] Path check failed: {e}")
        return {"error": f"Path check failed: {e}"}

    if not os.path.exists(abs_path):
        print(f"[ERROR] Path not found: {abs_path}")
        return {"error": "Path not found"}

    files = []
    try:
        # 使用 os.walk 递归遍历目录
        for root, dirs, filenames in os.walk(abs_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)

                # 计算相对于 output_dir 的路径，用于生成 URL (保留，虽然下载用绝对路径)
                rel_path = os.path.relpath(file_path, output_dir)
                url_path = rel_path.replace("\\", "/")

                files.append({
                    "name": filename,
                    "type": "file",
                    "path": file_path,
                    "url": f"/outputs/{url_path}",
                    "size": os.path.getsize(file_path),
                    "mtime": os.path.getmtime(file_path)
                })

    except Exception as e:
        print(f"[ERROR] Walk failed: {e}")
        return {"error": str(e)}

    # 按时间倒序排列
    files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    print(f"[DEBUG] Found {len(files)} files")
    return {"files": files}


@app.post("/api/memory/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """获取会话记忆统计信息（用户级隔离）"""
    user_id = current_user["sub"]
    memory_manager = get_memory_manager()
    stats = await memory_manager.get_session_stats(session_id, user_id)
    return MemoryStatsResponse(**stats)


@app.post("/api/memory/clear")
async def clear_session_memory(
    request: ClearSessionRequest,
    current_user: Dict = Depends(get_current_user)
):
    """清空会话记忆（用户级隔离）"""
    user_id = current_user["sub"]
    memory_manager = get_memory_manager()
    success = await memory_manager.clear_session(request.session_id, user_id)

    if success:
        return {"code": 200, "message": "Session memory cleared successfully"}
    else:
        return {"code": 500, "message": "Failed to clear session memory"}


@app.post("/api/memory/cleanup")
async def cleanup_old_memories(days: int = 30):
    """手动清理过期记忆"""
    memory_manager = get_memory_manager()
    deleted_count = await memory_manager.cleanup_old_sessions(days)

    return {
        "code": 200,
        "message": f"Cleaned up {deleted_count} old messages",
        "deleted_count": deleted_count
    }

# 这个接口是一个兼容性处理机制，用于强制要求旧版客户端升级到新的连接方式
@app.websocket("/ws")
async def websocket_legacy(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "error", "message": "Client outdated. Please refresh page."})
    await websocket.close(code=1000, reason="Client outdated")


# WebSocket连接不会出现在swagger文档中，但是实际运行时，会自动生成
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket, thread_id)
    try:
        while True:
            # 保持连接活跃，并可以接收前端指令
            # 目前只作为简单的保活 echo
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "message": f"received: {data}"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, thread_id)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(websocket, thread_id)


if __name__ == "__main__":
    # 初始化数据库表结构
    print("[Server] 初始化数据库...")
    if test_connection():
        if initialize_tables():
            print("[Server] 数据库表结构初始化成功!")
        else:
            print("[Server] 数据库表结构初始化失败!")
    else:
        print("[Server] 数据库连接失败，请检查配置!")

    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True)