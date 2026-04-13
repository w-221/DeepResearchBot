# utils/context_offload_manager.py
"""
Context Offload Manager - 上下文卸载管理器

功能：
1. 自动监控消息历史的 token 数量
2. 当超过阈值时，将中间结果卸载到 Redis
3. 按需从 Redis 加载历史内容
4. 管理卸载内容的生命周期（TTL）
"""

import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from utils.redis_store_backend import RedisStore
from api.context import get_session_context, get_thread_context

logger = logging.getLogger(__name__)

class ContextOffloadManager:
    """
    上下文卸载管理器

    工作原理：
    1. 监控对话历史的 token 数量
    2. 当超过阈值时，将旧的消息内容卸载到 Redis
    3. 在消息中保留引用指针（而非完整内容）
    4. Agent 需要时可以按需加载

    使用示例：
        manager = ContextOffloadManager(max_tokens=20000)
        messages = manager.optimize_messages(messages)
    """

    def __init__(
            self,
            max_tokens: int = 20000,
            warning_threshold: float = 0.7,
            offload_strategy: str = "oldest_first",
            redis_ttl: int = 3600
    ):
        """
        初始化上下文卸载管理器

        Args:
            max_tokens: 最大 token 阈值
            warning_threshold: 警告阈值比例（0.0-1.0）
            offload_strategy: 卸载策略
                - "oldest_first": 优先卸载最旧的消息
                - "largest_first": 优先卸载最大的消息
                - "tool_results_first": 优先卸载工具调用结果
            redis_ttl: Redis 中卸载内容的过期时间（秒）
        """
        self.max_tokens = max_tokens
        self.warning_threshold = warning_threshold
        self.offload_strategy = offload_strategy
        self.redis_ttl = redis_ttl

        # 初始化 Redis Store
        self.store = RedisStore(ttl=redis_ttl)

        # 统计信息
        self.stats = {
            "total_offloads": 0,
            "total_bytes_offloaded": 0,
            "current_context_tokens": 0
        }

        logger.info(
            f"ContextOffloadManager 初始化 (max_tokens={max_tokens}, "
            f"strategy={offload_strategy}, redis_ttl={redis_ttl}s)"
        )

    def estimate_tokens(self, text: str) -> int:
        """
        估算文本的 token 数量

        Args:
            text: 输入文本

        Returns:
            估算的 token 数量
        """
        if not text:
            return 0

        # 简单估算：中文 1 字符 ≈ 1 token，英文 4 字符 ≈ 1 token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        return chinese_chars + (other_chars // 4)

    def calculate_message_tokens(self, message: BaseMessage) -> int:
        """计算单条消息的 token 数量"""
        content = message.content if hasattr(message, 'content') else str(message)
        return self.estimate_tokens(str(content))

    def calculate_total_tokens(self, messages: List[BaseMessage]) -> int:
        """计算消息列表的总 token 数量"""
        return sum(self.calculate_message_tokens(msg) for msg in messages)

    def should_offload(self, messages: List[BaseMessage]) -> bool:
        """判断是否需要卸载"""
        total_tokens = self.calculate_total_tokens(messages)
        self.stats["current_context_tokens"] = total_tokens

        warning_level = total_tokens / self.max_tokens

        if warning_level >= self.warning_threshold:
            logger.warning(
                f"⚠️ Context usage high: {total_tokens}/{self.max_tokens} "
                f"({warning_level * 100:.1f}%)"
            )
            return True

        return False

    def select_messages_to_offload(
            self,
            messages: List[BaseMessage]
    ) -> List[Tuple[int, BaseMessage]]:
        """
        选择要卸载的消息

        Returns:
            [(index, message), ...] 要卸载的消息列表
        """
        if self.offload_strategy == "oldest_first":
            # 优先卸载最旧的（排除系统消息和最近的消息）
            candidates = []
            for i, msg in enumerate(messages):
                # 保留系统消息和最后 3 条消息
                if msg.type == "system" or i >= len(messages) - 3:
                    continue
                candidates.append((i, msg))

            # 按索引排序（最旧的在前）
            candidates.sort(key=lambda x: x[0])
            return candidates

        elif self.offload_strategy == "largest_first":
            # 优先卸载最大的消息
            candidates = []
            for i, msg in enumerate(messages):
                if msg.type == "system" or i >= len(messages) - 3:
                    continue
                tokens = self.calculate_message_tokens(msg)
                candidates.append((i, msg, tokens))

            # 按 token 数量降序排序
            candidates.sort(key=lambda x: x[2], reverse=True)
            return [(i, msg) for i, msg, _ in candidates]

        elif self.offload_strategy == "tool_results_first":
            # 优先卸载工具调用结果
            candidates = []
            for i, msg in enumerate(messages):
                if isinstance(msg, ToolMessage):
                    candidates.append((i, msg))

            # 按索引排序
            candidates.sort(key=lambda x: x[0])
            return candidates

        else:
            # 默认：oldest_first
            return self.select_messages_to_offload(messages)

    def offload_message(
            self,
            thread_id: str,
            index: int,
            message: BaseMessage
    ) -> str:
        """
        将消息卸载到 Redis

        Args:
            thread_id: 会话 ID
            index: 消息索引
            message: 消息对象

        Returns:
            Redis 中的引用 key
        """
        try:
            # 构建命名空间和 key
            namespace = (thread_id, "offloaded_messages")
            key = f"msg_{index}_{int(datetime.now().timestamp())}"

            # 序列化消息
            message_data = {
                "type": message.type,
                "content": str(message.content) if hasattr(message, 'content') else str(message),
                "additional_kwargs": getattr(message, 'additional_kwargs', {}),
                "offloaded_at": datetime.now().isoformat(),
                "original_index": index
            }

            # 存储到 Redis
            self.store.put(namespace, key, message_data, ttl=self.redis_ttl)

            # 更新统计
            content_size = len(message_data["content"])
            self.stats["total_offloads"] += 1
            self.stats["total_bytes_offloaded"] += content_size

            logger.debug(
                f"Offloaded message {index} to Redis: {key} "
                f"(size={content_size} bytes)"
            )

            return key

        except Exception as e:
            logger.error(f"Failed to offload message {index}: {e}")
            raise

    def create_offload_reference(
            self,
            original_message: BaseMessage,
            redis_key: str
    ) -> BaseMessage:
        """
        创建卸载后的引用消息（替换原消息）

        Args:
            original_message: 原始消息
            redis_key: Redis 中的 key

        Returns:
            包含引用的轻量级消息
        """
        reference_text = (
            f"[OFFLOADED TO REDIS]\n"
            f"Key: {redis_key}\n"
            f"Type: {original_message.type}\n"
            f"Original length: {len(str(original_message.content)) if hasattr(original_message, 'content') else 0} chars\n"
            f"Use 'load_offloaded_message' tool to retrieve full content."
        )

        # 保持原消息类型
        if isinstance(original_message, HumanMessage):
            return HumanMessage(content=reference_text)
        elif isinstance(original_message, AIMessage):
            return AIMessage(content=reference_text)
        elif isinstance(original_message, ToolMessage):
            return ToolMessage(content=reference_text, tool_call_id=getattr(original_message, 'tool_call_id', ''))
        else:
            return type(original_message)(content=reference_text)

    def load_offloaded_message(
            self,
            thread_id: str,
            redis_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        从 Redis 加载已卸载的消息

        Args:
            thread_id: 会话 ID
            redis_key: Redis key

        Returns:
            消息数据字典，或 None
        """
        try:
            namespace = (thread_id, "offloaded_messages")
            item = self.store.get(namespace, redis_key)

            if item:
                logger.debug(f"Loaded offloaded message from Redis: {redis_key}")
                return item.value
            else:
                logger.warning(f"Offloaded message not found in Redis: {redis_key}")
                return None

        except Exception as e:
            logger.error(f"Failed to load offloaded message {redis_key}: {e}")
            return None

    def optimize_messages(
            self,
            messages: List[BaseMessage],
            thread_id: Optional[str] = None
    ) -> List[BaseMessage]:
        """
        优化消息列表，自动卸载超出阈值的内容

        Args:
            messages: 原始消息列表
            thread_id: 会话 ID（如果为 None，尝试从上下文获取）

        Returns:
            优化后的消息列表
        """
        if not thread_id:
            thread_id = get_thread_context() or "default"

        # 检查是否需要卸载
        if not self.should_offload(messages):
            logger.debug("Context within limits, no offload needed")
            return messages

        # 计算需要释放的 token 数量
        current_tokens = self.stats["current_context_tokens"]
        target_tokens = int(self.max_tokens * 0.5)  # 目标：降到 50%
        tokens_to_free = current_tokens - target_tokens

        logger.info(
            f"Starting context offload: {current_tokens} tokens → target {target_tokens} tokens"
        )

        # 选择要卸载的消息
        candidates = self.select_messages_to_offload(messages)

        # 执行卸载
        optimized_messages = messages.copy()
        freed_tokens = 0
        offloaded_indices = []

        for index, message in candidates:
            if freed_tokens >= tokens_to_free:
                break

            # 计算这条消息的 token 数量
            msg_tokens = self.calculate_message_tokens(message)

            # 卸载到 Redis
            try:
                redis_key = self.offload_message(thread_id, index, message)

                # 创建引用消息
                reference_msg = self.create_offload_reference(message, redis_key)
                optimized_messages[index] = reference_msg

                freed_tokens += msg_tokens
                offloaded_indices.append(index)

                logger.debug(
                    f"Offloaded message {index}: freed {msg_tokens} tokens"
                )

            except Exception as e:
                logger.error(f"Failed to offload message {index}: {e}")
                continue

        logger.info(
            f"Context offload complete: freed {freed_tokens} tokens, "
            f"offloaded {len(offloaded_indices)} messages"
        )

        return optimized_messages

    def cleanup_expired(self, thread_id: str) -> int:
        """
        清理已过期的卸载内容

        Args:
            thread_id: 会话 ID

        Returns:
            清理的数量
        """
        try:
            namespace = (thread_id, "offloaded_messages")
            return self.store.clear_namespace(namespace)
        except Exception as e:
            logger.error(f"Cleanup failed for {thread_id}: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
