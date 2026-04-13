# utils/redis_store_backend.py
"""
Redis Store Backend for DeepAgents
基于 LangGraph BaseStore 实现的 Redis 持久化存储后端
用于解决长任务导致的 Context Window 溢出问题
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta

from langgraph.store.base import BaseStore, Item, SearchItem, Op, Result, NamespacePath
from api.redis_client import get_redis_client
import redis

logger = logging.getLogger(__name__)


class RedisStore(BaseStore):
    """
    基于 Redis 的 LangGraph Store 实现

    特性:
    - 支持 TTL (Time-To-Live) 自动过期
    - 命名空间隔离 (namespace/key)
    - 跨线程/会话持久化
    - 支持语义搜索（可选，需要向量索引）

    使用示例:
        store = RedisStore(ttl=3600)  # 1小时过期
        store.put(("session_123", "intermediate"), {"result": "data"})
        item = store.get(("session_123", "intermediate"))
    """

    def __init__(
            self,
            ttl: int = 3600,
            namespace_prefix: str = "deepagents:",
            enable_search: bool = False
    ):
        """
        初始化 Redis Store

        Args:
            ttl: 默认过期时间（秒），0表示永不过期
            namespace_prefix: Redis key 前缀，用于隔离不同应用
            enable_search: 是否启用语义搜索（需要额外配置向量索引）
        """
        self.client = get_redis_client()
        self.ttl = ttl
        self.namespace_prefix = namespace_prefix
        self.enable_search = enable_search

        if not self.client:
            logger.warning("Redis 不可用，RedisStore 将降级为内存模式")
            self._memory_store: Dict[str, Any] = {}

        logger.info(f"RedisStore 初始化完成 (TTL={ttl}s, prefix={namespace_prefix})")

    def _build_key(self, namespace: tuple, key: str) -> str:
        """
        构建 Redis key

        Args:
            namespace: 命名空间元组，如 ("session_123", "intermediate")
            key: 键名

        Returns:
            Redis key 字符串
        """
        ns_str = ":".join(str(n) for n in namespace)
        return f"{self.namespace_prefix}{ns_str}:{key}"

    def _serialize_value(self, value: Any) -> str:
        """序列化值为 JSON 字符串"""
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"序列化失败: {e}")
            return json.dumps({"error": "Serialization failed", "type": str(type(value))})

    def _deserialize_value(self, value: str) -> Any:
        """反序列化 JSON 字符串为值"""
        try:
            return json.loads(value)
        except Exception as e:
            logger.error(f"反序列化失败: {e}")
            return {"error": "Deserialization failed"}

    def get(self, namespace: tuple, key: str) -> Optional[Item]:
        """
        获取单个项

        Args:
            namespace: 命名空间
            key: 键名

        Returns:
            Item 对象或 None
        """
        try:
            redis_key = self._build_key(namespace, key)

            if hasattr(self, '_memory_store'):
                # 内存模式
                value = self._memory_store.get(redis_key)
                if value is None:
                    return None
                return Item(
                    namespace=list(namespace),
                    key=key,
                    value=value,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

            # Redis 模式
            value_str = self.client.get(redis_key)
            if value_str is None:
                return None

            value = self._deserialize_value(value_str)

            # 获取 TTL
            ttl = self.client.ttl(redis_key)

            return Item(
                namespace=list(namespace),
                key=key,
                value=value,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                ttl=ttl if ttl > 0 else None
            )
        except Exception as e:
            logger.error(f"Redis GET 失败 [{namespace}:{key}]: {e}")
            return None

    def put(
            self,
            namespace: tuple,
            key: str,
            value: Any,
            ttl: Optional[int] = None,
            **kwargs
    ) -> None:
        """
        存储项

        Args:
            namespace: 命名空间
            key: 键名
            value: 值（任意可序列化的对象）
            ttl: 过期时间（秒），None 使用默认值
        """
        try:
            redis_key = self._build_key(namespace, key)
            value_str = self._serialize_value(value)
            expire_time = ttl if ttl is not None else self.ttl

            if hasattr(self, '_memory_store'):
                # 内存模式
                self._memory_store[redis_key] = value
                logger.debug(f"[Memory] PUT {redis_key} (size={len(value_str)} bytes)")
            else:
                # Redis 模式
                if expire_time and expire_time > 0:
                    self.client.setex(redis_key, expire_time, value_str)
                else:
                    self.client.set(redis_key, value_str)

                logger.debug(f"[Redis] PUT {redis_key} (TTL={expire_time}s, size={len(value_str)} bytes)")

        except Exception as e:
            logger.error(f"Redis PUT 失败 [{namespace}:{key}]: {e}")
            raise

    def delete(self, namespace: tuple, key: str) -> None:
        """删除项"""
        try:
            redis_key = self._build_key(namespace, key)

            if hasattr(self, '_memory_store'):
                self._memory_store.pop(redis_key, None)
            else:
                self.client.delete(redis_key)

            logger.debug(f"DELETE {redis_key}")
        except Exception as e:
            logger.error(f"Redis DELETE 失败 [{namespace}:{key}]: {e}")

    def search(
            self,
            namespace_prefix: tuple,
            query: Optional[str] = None,
            limit: int = 10,
            offset: int = 0,
            **kwargs
    ) -> List[SearchItem]:
        """
        搜索项（基于 key 模式匹配）

        Args:
            namespace_prefix: 命名空间前缀
            query: 搜索查询（当前仅支持 key 模式匹配）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索结果列表
        """
        try:
            ns_prefix = ":".join(str(n) for n in namespace_prefix)
            pattern = f"{self.namespace_prefix}{ns_prefix}:*"

            if hasattr(self, '_memory_store'):
                # 内存模式
                results = []
                for redis_key, value in self._memory_store.items():
                    if redis_key.startswith(pattern):
                        parts = redis_key[len(self.namespace_prefix):].split(":")
                        if len(parts) >= 2:
                            key = parts[-1]
                            namespace = parts[:-1]
                            results.append(SearchItem(
                                namespace=namespace,
                                key=key,
                                value=value,
                                score=1.0
                            ))
                return results[offset:offset + limit]

            # Redis 模式 - 使用 SCAN 代替 KEYS（生产环境更安全）
            results = []
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)

                for redis_key in keys:
                    value_str = self.client.get(redis_key)
                    if value_str:
                        value = self._deserialize_value(value_str)

                        # 解析 namespace 和 key
                        key_part = redis_key[len(self.namespace_prefix):]
                        parts = key_part.split(":")
                        if len(parts) >= 2:
                            key = parts[-1]
                            namespace = parts[:-1]

                            results.append(SearchItem(
                                namespace=namespace,
                                key=key,
                                value=value,
                                score=1.0
                            ))

                if cursor == 0 or len(results) >= limit + offset:
                    break

            return results[offset:offset + limit]

        except Exception as e:
            logger.error(f"Redis SEARCH 失败 [{namespace_prefix}]: {e}")
            return []

    def list_namespaces(
            self,
            prefix: Optional[tuple] = None,
            suffix: Optional[tuple] = None,
            max_depth: Optional[int] = None,
            limit: int = 100,
            offset: int = 0
    ) -> List[NamespacePath]:
        """列出命名空间"""
        # 简化实现：返回空列表
        # 完整实现需要解析所有 key 并提取命名空间层级
        return []

    def batch(self, ops: List[Op]) -> List[Result]:
        """批量操作"""
        results = []
        for op in ops:
            try:
                if op.op == "get":
                    item = self.get(op.namespace, op.key)
                    results.append(Result(value=item.value if item else None))
                elif op.op == "put":
                    self.put(op.namespace, op.key, op.value, ttl=op.kwargs.get("ttl"))
                    results.append(Result(value=None))
                elif op.op == "delete":
                    self.delete(op.namespace, op.key)
                    results.append(Result(value=None))
                else:
                    results.append(Result(error=f"Unsupported operation: {op.op}"))
            except Exception as e:
                results.append(Result(error=str(e)))

        return results

    async def abatch(self, ops: List[Op]) -> List[Result]:
        """异步批量操作（Redis 客户端为同步，直接复用 batch 逻辑）"""
        return self.batch(ops)

    @property
    def supports_ttl(self) -> bool:
        """是否支持 TTL"""
        return True

    def clear_namespace(self, namespace: tuple) -> int:
        """
        清空整个命名空间

        Args:
            namespace: 命名空间

        Returns:
            删除的 key 数量
        """
        try:
            ns_prefix = ":".join(str(n) for n in namespace)
            pattern = f"{self.namespace_prefix}{ns_prefix}:*"

            if hasattr(self, '_memory_store'):
                keys_to_delete = [k for k in self._memory_store.keys() if k.startswith(pattern)]
                for key in keys_to_delete:
                    del self._memory_store[key]
                return len(keys_to_delete)

            # Redis 模式
            deleted_count = 0
            cursor = 0
            while True:
                cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self.client.delete(*keys)
                if cursor == 0:
                    break

            logger.info(f"Cleared namespace {namespace}: {deleted_count} keys deleted")
            return deleted_count

        except Exception as e:
            logger.error(f"Clear namespace failed [{namespace}]: {e}")
            return 0
