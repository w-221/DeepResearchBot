import os
import logging
from typing import Optional
import redis

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端单例"""

    _instance: Optional[redis.Redis] = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        """获取 Redis 客户端实例"""
        if cls._instance is None:
            try:
                redis_config = {
                    'host': os.getenv('REDIS_HOST', 'localhost'),
                    'port': int(os.getenv('REDIS_PORT', 6379)),
                    'db': int(os.getenv('REDIS_DB', 0)),
                    'decode_responses': True,
                }

                # 如果设置了密码，添加密码配置
                password = os.getenv('REDIS_PASSWORD')
                if password:
                    redis_config['password'] = password

                cls._instance = redis.Redis(**redis_config)

                # 测试连接
                cls._instance.ping()
                logger.info("Redis 连接成功")

            except redis.ConnectionError as e:
                logger.error(f"Redis 连接失败: {e}")
                logger.warning("将使用内存模式运行（生产环境请配置 Redis）")
                cls._instance = None
            except Exception as e:
                logger.error(f"Redis 初始化失败: {e}")
                cls._instance = None

        return cls._instance

    @classmethod
    def is_available(cls) -> bool:
        """检查 Redis 是否可用"""
        client = cls.get_client()
        return client is not None


def get_redis_client() -> Optional[redis.Redis]:
    """获取 Redis 客户端的便捷函数"""
    return RedisClient.get_client()
