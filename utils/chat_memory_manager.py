"""
utils/chat_memory_manager.py
聊天记忆管理器 - 基于MongoDB的持久化对话历史存储
支持Redis缓存加速和批量写入优化
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from api.mongodb_client import get_chat_collection
from api.redis_client import get_redis_client
from api.logger import AgentLogger
import logging

logger = logging.getLogger(__name__)


class ChatMemoryManager:
    """
    聊天记忆管理器

    功能:
    - 持久化存储对话历史到MongoDB
    - Redis缓存加速读取
    - 支持分页加载历史消息
    - 自动清理过期数据（通过MongoDB TTL）
    - 批量写入优化
    """

    def __init__(
            self,
            redis_cache_ttl: int = 300,
            max_messages_per_session: int = 1000,
            batch_write_size: int = 10,
            batch_write_interval: float = 2.0
    ):
        """
        初始化记忆管理器

        Args:
            redis_cache_ttl: Redis缓存TTL（秒）
            max_messages_per_session: 每个会话最大消息数
            batch_write_size: 批量写入阈值
            batch_write_interval: 批量写入时间间隔（秒）
        """
        self.redis_client = get_redis_client()
        self.redis_cache_ttl = redis_cache_ttl
        self.max_messages_per_session = max_messages_per_session
        self.batch_write_size = batch_write_size

        # 批量写入缓冲区
        self._write_buffer: Dict[str, List[Dict]] = {}
        self._last_flush_time: Dict[str, float] = {}
        self._batch_write_interval = batch_write_interval

        logger.info(f"ChatMemoryManager initialized (cache_ttl={redis_cache_ttl}s, batch_size={batch_write_size})")

    def _get_redis_key(self, session_id: str, user_id: str = None) -> str:
        """生成带用户隔离的Redis缓存key"""
        if user_id:
            return f"chat_memory:{user_id}:{session_id}"
        return f"chat_memory:anonymous:{session_id}"

    async def save_message(
            self,
            session_id: str,
            user_id: Optional[str] = None,
            role: str = "user",
            content: str = "",
            metadata: Optional[Dict] = None,
            immediate: bool = False
    ) -> bool:
        """
        保存单条消息（支持批量缓冲）

        Args:
            session_id: 会话ID
            user_id: 用户ID（必填，用于数据隔离）
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据
            immediate: 是否立即写入（绕过缓冲）

        Returns:
            是否成功保存
        """
        try:
            # 强制要求 user_id，确保数据隔离
            if not user_id:
                logger.warning(f"user_id is required for session {session_id}, using 'anonymous'")
                user_id = "anonymous"

            message = {
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }

            if immediate:
                return await self._flush_single_message(message)
            else:
                # 添加到缓冲区（按 user_id:session_id 分组）
                buffer_key = f"{user_id}:{session_id}"
                if buffer_key not in self._write_buffer:
                    self._write_buffer[buffer_key] = []
                    self._last_flush_time[buffer_key] = time.time()

                self._write_buffer[buffer_key].append(message)

                # 检查是否需要刷新缓冲区
                if len(self._write_buffer[buffer_key]) >= self.batch_write_size:
                    await self.flush_session(session_id, user_id)

                return True

        except Exception as e:
            logger.error(f"Failed to save message for session {session_id}: {e}")
            return False

    async def _flush_single_message(self, message: Dict) -> bool:
        """立即写入单条消息到MongoDB"""
        try:
            collection = await get_chat_collection()

            # 获取当前用户会话的消息数量（双重过滤）
            session_id = message["session_id"]
            user_id = message["user_id"]

            count = await collection.count_documents({
                "session_id": session_id,
                "user_id": user_id
            })

            # 检查是否超过最大消息数
            if count >= self.max_messages_per_session:
                # 删除该用户最早的消息
                oldest = await collection.find_one(
                    {"session_id": session_id, "user_id": user_id},
                    sort=[("message_index", 1)]
                )
                if oldest:
                    await collection.delete_one({"_id": oldest["_id"]})

            # 计算消息索引
            message["message_index"] = count

            # 插入消息
            result = await collection.insert_one(message)

            # 清除Redis缓存（使用用户隔离的key）
            if self.redis_client:
                redis_key = self._get_redis_key(session_id, user_id)
                self.redis_client.delete(redis_key)

            logger.debug(f"Message saved to MongoDB: {result.inserted_id} (user={user_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to flush single message: {e}")
            return False

    async def flush_session(self, session_id: str, user_id: str = None) -> bool:
        """刷新指定会话的缓冲区到MongoDB"""
        # 构建缓冲区key
        buffer_key = f"{user_id}:{session_id}" if user_id else session_id

        if buffer_key not in self._write_buffer or not self._write_buffer[buffer_key]:
            return True

        messages = self._write_buffer.pop(buffer_key, [])
        self._last_flush_time.pop(buffer_key, None)

        if not messages:
            return True

        try:
            collection = await get_chat_collection()

            # 提取 user_id（从第一条消息）
            msg_user_id = messages[0].get("user_id", "anonymous")

            # 批量插入
            # 获取起始索引（用户级隔离）
            count = await collection.count_documents({
                "session_id": session_id,
                "user_id": msg_user_id
            })

            for idx, msg in enumerate(messages):
                msg["message_index"] = count + idx

            result = await collection.insert_many(messages)

            # 清除Redis缓存
            if self.redis_client:
                redis_key = self._get_redis_key(session_id, msg_user_id)
                self.redis_client.delete(redis_key)

            logger.debug(f"Batch saved {len(messages)} messages for session {session_id} (user={msg_user_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to flush session {session_id}: {e}")
            # 重新加入缓冲区
            self._write_buffer[buffer_key] = messages
            return False

    async def flush_all(self):
        """刷新所有缓冲区"""
        session_ids = list(self._write_buffer.keys())
        for buffer_key in session_ids:
            # 解析 buffer_key 格式: "user_id:session_id"
            if ":" in buffer_key:
                parts = buffer_key.split(":", 1)
                user_id = parts[0]
                session_id = parts[1]
                await self.flush_session(session_id, user_id)
            else:
                await self.flush_session(buffer_key)

    async def get_messages(
            self,
            session_id: str,
            user_id: str = None,
            limit: int = 50,
            offset: int = 0,
            use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取会话历史消息

        Args:
            session_id: 会话ID
            user_id: 用户ID（必填，用于数据隔离）
            limit: 返回消息数量限制
            offset: 偏移量
            use_cache: 是否使用Redis缓存

        Returns:
            消息列表（按时间倒序）
        """
        # 强制要求 user_id
        if not user_id:
            logger.warning(f"user_id is required for session {session_id}, using 'anonymous'")
            user_id = "anonymous"

        try:
            # 尝试从Redis缓存读取（用户隔离的key）
            if use_cache and self.redis_client:
                redis_key = self._get_redis_key(session_id, user_id)
                cached_data = self.redis_client.get(redis_key)

                if cached_data:
                    logger.debug(f"Cache hit for session {session_id} (user={user_id})")
                    messages = json.loads(cached_data)
                    # 应用limit和offset
                    return messages[offset:offset + limit]

            # 从MongoDB查询（双重过滤：session_id + user_id）
            collection = await get_chat_collection()
            cursor = collection.find({
                "session_id": session_id,
                "user_id": user_id
            }).sort(
                "message_index", -1
            ).skip(
                offset
            ).limit(
                limit
            )

            messages = []
            async for doc in cursor:
                # 移除MongoDB内部字段
                doc.pop("_id", None)
                # 转换datetime为字符串
                if "created_at" in doc:
                    doc["created_at"] = doc["created_at"].isoformat()
                if "updated_at" in doc:
                    doc["updated_at"] = doc["updated_at"].isoformat()
                messages.append(doc)

            # 反转列表（变为正序）
            messages.reverse()

            # 写入Redis缓存（用户隔离的key）
            if self.redis_client and messages:
                redis_key = self._get_redis_key(session_id, user_id)
                cache_data = json.dumps(messages, ensure_ascii=False)
                self.redis_client.setex(
                    redis_key,
                    self.redis_cache_ttl,
                    cache_data
                )

            return messages

        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id} (user={user_id}): {e}")
            return []

    async def get_recent_context(
            self,
            session_id: str,
            user_id: str = None,
            max_messages: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取最近的对话上下文（用于LLM输入）

        Args:
            session_id: 会话ID
            user_id: 用户ID（必填，用于数据隔离）
            max_messages: 最大消息数

        Returns:
            最近的消息列表
        """
        messages = await self.get_messages(
            session_id=session_id,
            user_id=user_id,
            limit=max_messages,
            offset=0,
            use_cache=True
        )

        # 转换为LangChain消息格式
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        langchain_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))
            elif role == "system":
                langchain_messages.append(SystemMessage(content=content))

        return langchain_messages

    async def clear_session(self, session_id: str, user_id: str = None) -> bool:
        """清空会话历史（用户级隔离）"""
        if not user_id:
            logger.warning(f"user_id is required for clearing session {session_id}, using 'anonymous'")
            user_id = "anonymous"

        try:
            collection = await get_chat_collection()
            # 只删除该用户的消息
            result = await collection.delete_many({
                "session_id": session_id,
                "user_id": user_id
            })

            # 清除Redis缓存
            if self.redis_client:
                redis_key = self._get_redis_key(session_id, user_id)
                self.redis_client.delete(redis_key)

            logger.info(f"Cleared {result.deleted_count} messages for session {session_id} (user={user_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to clear session {session_id} (user={user_id}): {e}")
            return False

    async def get_session_stats(self, session_id: str, user_id: str = None) -> Dict[str, Any]:
        """获取会话统计信息（用户级隔离）"""
        if not user_id:
            user_id = "anonymous"

        try:
            collection = await get_chat_collection()

            # 消息总数（用户级过滤）
            total_messages = await collection.count_documents({
                "session_id": session_id,
                "user_id": user_id
            })

            # 最早和最晚消息时间
            pipeline = [
                {"$match": {"session_id": session_id, "user_id": user_id}},
                {"$group": {
                    "_id": None,
                    "first_message": {"$min": "$created_at"},
                    "last_message": {"$max": "$created_at"}
                }}
            ]

            stats = await collection.aggregate(pipeline).to_list(length=1)

            if stats:
                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "total_messages": total_messages,
                    "first_message": stats[0]["first_message"].isoformat(),
                    "last_message": stats[0]["last_message"].isoformat()
                }
            else:
                return {
                    "session_id": session_id,
                    "user_id": user_id,
                    "total_messages": 0,
                    "first_message": None,
                    "last_message": None
                }

        except Exception as e:
            logger.error(f"Failed to get stats for session {session_id} (user={user_id}): {e}")
            return {"session_id": session_id, "user_id": user_id, "total_messages": 0}

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        清理过期会话（手动触发，作为TTL的补充）

        Args:
            days: 保留天数

        Returns:
            删除的文档数
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            collection = await get_chat_collection()
            result = await collection.delete_many({
                "created_at": {"$lt": cutoff_date}
            })

            logger.info(f"Cleaned up {result.deleted_count} old messages (older than {days} days)")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0


# 全局实例
_memory_manager: Optional[ChatMemoryManager] = None


def get_memory_manager() -> ChatMemoryManager:
    """获取全局记忆管理器实例（单例）"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = ChatMemoryManager()
    return _memory_manager
