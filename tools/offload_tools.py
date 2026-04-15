# tools/offload_tools.py
"""
Offload Tools - 允许 Agent 主动管理卸载的内容
"""

from typing import Annotated
from langchain_core.tools import tool
from utils.context_offload_manager import ContextOffloadManager
from api.context import get_thread_context
from api.monitor import monitor


@tool
def load_offloaded_message(
        redis_key: Annotated[str, "Redis 中卸载消息的 key，格式如: msg_123_1234567890"]
) -> str:
    """
    从 Redis 加载之前卸载的消息内容

    当你在对话中看到 [OFFLOADED TO REDIS] 标记时，使用此工具恢复完整内容。

    Args:
        redis_key: Redis key，从引用消息中获取

    Returns:
        完整的消息内容
    """
    monitor.report_tool("load_offloaded_message", {"redis_key": redis_key})

    thread_id = get_thread_context()
    if not thread_id:
        return "错误：无法获取当前会话 ID"

    try:
        manager = ContextOffloadManager()
        message_data = manager.load_offloaded_message(thread_id, redis_key)

        if message_data:
            content = message_data.get("content", "")
            msg_type = message_data.get("type", "unknown")
            offloaded_at = message_data.get("offloaded_at", "unknown")

            return (
                f"[RESTORED FROM REDIS]\n"
                f"Type: {msg_type}\n"
                f"Offloaded at: {offloaded_at}\n"
                f"Content:\n{content}"
            )
        else:
            return f"错误：未找到 key 为 '{redis_key}' 的卸载内容（可能已过期）"

    except Exception as e:
        return f"加载失败: {str(e)}"


@tool
def get_offload_stats() -> str:
    """
    获取当前会话的上下文卸载统计信息

    Returns:
        统计信息字符串
    """
    monitor.report_tool("get_offload_stats")

    try:
        manager = ContextOffloadManager()
        stats = manager.get_stats()

        return (
            f"上下文卸载统计:\n"
            f"- 总卸载次数: {stats['total_offloads']}\n"
            f"- 卸载数据总量: {stats['total_bytes_offloaded']} bytes\n"
            f"- 当前上下文 tokens: {stats['current_context_tokens']}"
        )
    except Exception as e:
        return f"获取统计信息失败: {str(e)}"


@tool
def trigger_context_offload() -> str:
    """
    主动触发上下文卸载操作

    当对话历史过长时，调用此工具将旧消息卸载到 Redis，
    减少当前上下文的 token 数量，避免超出模型限制。

    Returns:
        卸载操作的结果信息
    """
    monitor.report_tool("trigger_context_offload")

    thread_id = get_thread_context()
    if not thread_id:
        return "错误：无法获取当前会话 ID"

    try:
        manager = ContextOffloadManager()

        # 注意：这里需要从 LangGraph State 中获取当前消息列表
        # 但由于工具函数无法直接访问 State，我们需要通过其他方式实现
        # 方案：返回提示信息，让主流程在适当位置自动调用 optimize_messages

        stats = manager.get_stats()
        return (
            f"上下文卸载提示:\n"
            f"- 当前上下文 tokens: {stats['current_context_tokens']}\n"
            f"- 总卸载次数: {stats['total_offloads']}\n\n"
            f"注意：实际的卸载操作由系统在检测到 token 超限时自动执行。\n"
            f"如需手动管理，请使用 load_offloaded_message 工具恢复内容。"
        )
    except Exception as e:
        return f"触发卸载失败: {str(e)}"


@tool
def cleanup_offloaded_content() -> str:
    """
    清理当前会话的所有卸载内容（释放 Redis 空间）

    警告：此操作不可逆，清理后将无法恢复卸载的内容。

    Returns:
        清理结果
    """
    monitor.report_tool("cleanup_offloaded_content")

    thread_id = get_thread_context()
    if not thread_id:
        return "错误：无法获取当前会话 ID"

    try:
        manager = ContextOffloadManager()
        deleted_count = manager.cleanup_expired(thread_id)

        return f"已清理 {deleted_count} 个卸载的内容项"
    except Exception as e:
        return f"清理失败: {str(e)}"
