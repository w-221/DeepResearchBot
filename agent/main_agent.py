# 导入子智能体（使用本地 RAG 替代 RAGFlow）
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend


from agent.sub_agents.local_knowledge_base_agent import local_knowledge_base_agent
from agent.sub_agents.database_query_agent import database_query_agent
from agent.sub_agents.network_search_agent import network_search_agent
import logging

# 使用标准 logging.Logger（原 from api import logger 会导入 api.logger 模块而非 logger 实例，
# 导致 logger.warning/info 在运行时报 AttributeError）
logger = logging.getLogger(__name__)

# main_agent tool导入
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tools import read_file_content
from tools.local_rag_tools import list_session_files, add_file_to_kb, search_knowledge_base
from tools.offload_tools import load_offloaded_message,get_offload_stats,cleanup_offloaded_content,trigger_context_offload

from deepagents import create_deep_agent

from agent.llm import model
from agent.prompts import main_agent_config

from api.monitor import monitor
import asyncio
import uuid
import shutil
from pathlib import Path

from api.context import set_session_context, reset_session_context, set_thread_context

from langchain_core.messages import AIMessage, HumanMessage

from api.logger import AgentLogger, AgentLogCallbackHandler
from utils.context_offload_manager import get_offload_manager
from utils.redis_store_backend import RedisStore
from utils.chat_memory_manager import get_memory_manager


# 初始化本地知识库（启动时加载向量数据库）
try:
    from tools.local_rag_tools import init_knowledge_base
    init_knowledge_base()
except Exception as e:
    print(f"[WARNING] 本地知识库初始化失败: {e}")

# 1. 搭建多智能体结构
subagents_list = [
    local_knowledge_base_agent,  # 使用本地 RAG 替代 RAGFlow
    database_query_agent,
    network_search_agent
]

# 2. 配置Skills目录路径
project_root = Path(__file__).parent.parent
skills_directory = project_root / "skills"

# 创建复合后端工厂函数：临时文件用 StateBackend，长期记忆用 Redis Store
def create_composite_backend(runtime):
    """
    创建复合后端，支持中间结果卸载到 Redis

    路由规则：
    - 默认路径 (/workspace/*) → StateBackend (临时存储，仅当前线程)
    - 记忆路径 (/memories/*) → StoreBackend (Redis 持久化，跨线程)
    - 卸载路径 (/offload/*) → StoreBackend (Redis 持久化，带 TTL)
    """
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime),
            "/offload/": StoreBackend(runtime),
        }
    )

# 创建主智能体
main_agent = create_deep_agent(
    model=model,
    subagents=subagents_list,
    tools=[generate_markdown,
           convert_md_to_pdf,
           read_file_content,
           list_session_files,
           add_file_to_kb,
           search_knowledge_base,
           load_offloaded_message,
           get_offload_stats,
           trigger_context_offload,
           cleanup_offloaded_content
           ],
    system_prompt=main_agent_config["system_prompt"],
    backend=create_composite_backend,
    store=RedisStore(ttl=3600),
    skills=[str(skills_directory)]
)

def _scan_session_files(session_dir: str) -> str:
    """
    扫描当前会话目录下用户已上传的文件，生成用于注入 LLM 上下文的文件列表描述。

    上传接口会将文件直接保存到 updated/session_{thread_id}/ 目录顶层，
    而 generate_markdown 等工具生成的中间产物位于 output/ 子目录下。
    因此这里只统计顶层文件（os.path.isfile 会天然排除 output 等子目录）。

    Args:
        session_dir: 会话目录路径（updated/session_{thread_id}）

    Returns:
        str: 文件列表描述文本；若目录不存在或没有文件，返回空字符串
    """
    import os

    if not session_dir or not os.path.exists(session_dir):
        return ""

    uploaded_files = [
        filename
        for filename in os.listdir(session_dir)
        if os.path.isfile(os.path.join(session_dir, filename))
    ]

    if not uploaded_files:
        return ""

    files_list = "\n".join(f"- {name}" for name in uploaded_files)
    return (
        "【当前会话已上传文件】\n"
        f"用户已向当前会话上传以下文件（保存在会话目录 {session_dir} 中）：\n"
        f"{files_list}\n\n"
        "当用户提到“文档”“文件”或要求基于文档内容进行总结、分析、回答时，"
        "请先调用 read_file_content 工具读取上述对应文件的内容，"
        "再基于读取到的内容进行回答；严禁直接总结系统提示词或凭空猜测。"
    )


async def run_deep_agent(query: str, thread_id: str,user_id: str = None):
    """
    运行 Deep Agent 任务。

    Args:
        query: 用户的查询/提示词
        thread_id: 会话线程 ID，用于隔离不同用户的请求
        user_id: 用户ID（可选，用于记忆关联）
    """
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. 创建会话目录及 output 子目录
    updated_dir = os.path.join(project_root, "updated")
    session_dir = os.path.join(updated_dir, f"session_{thread_id}")
    output_sub_dir = os.path.join(session_dir, "output")
    if not os.path.exists(output_sub_dir):
        os.makedirs(output_sub_dir)

    # 2. 设置上下文变量（必须在推送 WebSocket 消息之前设置，保证不同用户的WebSocket通信管道隔离）
    session_token = set_session_context(session_dir)
    thread_token = set_thread_context(thread_id)

    # 3. 推送工作目录信息（现在 thread_id 已经设置）
    monitor.report_session_dir(session_dir)

    # 4. 初始化日志记录器
    agent_logger = AgentLogger(thread_id, project_root)
    callback_handler = AgentLogCallbackHandler(agent_logger)

    # 5. 初始化记忆管理器
    memory_manager = get_memory_manager()

    try:
        # 处理用户id不存在的情况，提供默认值
        if not user_id:
            user_id = "anonymous"
            logger.warning(f"user_id not provided for session {thread_id}, using 'anonymous'")

        # 6. 加载历史对话上下文
        recent_messages = await memory_manager.get_recent_context(
            session_id=thread_id,
            user_id=user_id,
            max_messages=20
        )

        # 扫描当前会话已上传的文件，作为上下文注入到用户消息中，
        # 确保 Agent 能感知到"用户上传了哪些文件"并据此触发 read_file_content 工具
        session_files_info = _scan_session_files(session_dir)

        # 构建完整的消息列表（历史 + 当前查询）
        enhanced_query = f"{session_files_info}\n\n【用户问题】\n{query}" if session_files_info else query

        # 构建统一的消息列表：历史消息已是 BaseMessage，当前用户输入也转换为 HumanMessage，
        # 保证传给上下文卸载管理器和 ainvoke 的都是统一的 LangChain 消息类型
        current_query_message = HumanMessage(content=enhanced_query)
        if recent_messages:
            messages = recent_messages + [current_query_message]
        else:
            messages = [current_query_message]

        # 保存用户消息到记忆
        await memory_manager.save_message(
            session_id=thread_id,
            user_id=user_id,
            role="user",
            content=query,
            immediate=False
        )

        #【新增】自动优化上下文 - 卸载超限内容
        offload_manager = get_offload_manager(max_tokens=20000)
        optimized_messages = offload_manager.optimize_messages(messages, thread_id)

        offload_stats = offload_manager.get_stats()
        if offload_stats["total_offloads"] > 0:
            logger.info(f"Context offload triggered: freed to {offload_stats['current_context_tokens']} tokens, "
                        f"total offloads={offload_stats['total_offloads']}")

        # 7. 执行 Agent
        monitor.report_assistant("main_agent", {"query": query})

        # 调用 main_agent 的 ainvoke 方法执行查询（异步版本）
        # 注意：必须传入优化后的 optimized_messages，否则自动卸载结果会被丢弃
        result = await main_agent.ainvoke(
            {"messages": optimized_messages},
            config={"callbacks": [callback_handler]}
        )

        # 8. 处理结果
        # 打印调试信息
        print(f"[DEBUG] result type: {type(result)}, result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")

        if isinstance(result, dict):
            # deepagents 的 ainvoke 返回的 result 结构：
            # - result["messages"]: 消息列表 [HumanMessage, AIMessage, ...]
            # - result.get("messages")[-1].content: 最后一条消息的内容（通常是 AI 的回复）

            messages = result.get("messages", [])
            print(f"[DEBUG] messages type: {type(messages)}, len: {len(messages)}")

            if messages and isinstance(messages, list) and len(messages) > 0:
                # 获取最后一条消息（通常是 AI 的回复）
                last_message = messages[-1]
                print(f"[DEBUG] last_message type: {type(last_message)}")

                # 如果消息有 content 属性，使用它
                if hasattr(last_message, 'content'):
                    output = str(last_message.content)
                elif isinstance(last_message, str):
                    output = last_message
                else:
                    output = str(last_message)
            else:
                # 如果没有消息，尝试获取 output 字段
                output = result.get("output", "")
                if not output:
                    output = str(result)
        else:
            output = str(result)

        print(f"[DEBUG] Final output: {output[:200] if len(output) > 200 else output}...")
        monitor.report_task_result(output)   # 推送任务最终结果
        agent_logger._write_log("FINAL_RESULT", output)

        # 9. 保存AI回复到记忆
        await memory_manager.save_message(
            session_id=thread_id,
            user_id=user_id,
            role="assistant",
            content=output,
            immediate=False
        )

        # 10. 刷新缓冲区确保数据持久化
        await memory_manager.flush_session(thread_id,user_id)

        return output

    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}"
        print(f"[ERROR] {error_msg}")
        agent_logger._write_log("ERROR", error_msg)
        raise

    finally:
        # 7. 清理上下文变量
        reset_session_context(session_token, thread_token)