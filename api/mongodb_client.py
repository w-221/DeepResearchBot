"""
api/mongodb_client.py
MongoDB 客户端管理模块
提供异步MongoDB连接池和集合访问
"""

import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# 全局变量
_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[MongoClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


def get_mongodb_uri() -> str:
    """获取MongoDB连接URI"""
    return os.getenv("MONGODB_URI", "mongodb://localhost:27017")


def get_mongodb_database_name() -> str:
    """获取数据库名称"""
    return os.getenv("MONGODB_DATABASE", "chat_memory_db")


async def get_async_client() -> AsyncIOMotorClient:
    """获取异步MongoDB客户端（单例模式）"""
    global _async_client
    if _async_client is None:
        uri = get_mongodb_uri()
        _async_client = AsyncIOMotorClient(
            uri,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=30000
        )
    return _async_client


def get_sync_client() -> MongoClient:
    """获取同步MongoDB客户端（单例模式）"""
    global _sync_client
    if _sync_client is None:
        uri = get_mongodb_uri()
        _sync_client = MongoClient(
            uri,
            maxPoolSize=20,
            minPoolSize=5,
            serverSelectionTimeoutMS=5000
        )
    return _sync_client


async def get_database() -> AsyncIOMotorDatabase:
    """获取数据库实例"""
    global _database
    if _database is None:
        client = await get_async_client()
        db_name = get_mongodb_database_name()
        _database = client[db_name]
    return _database


async def get_chat_collection():
    """获取聊天记忆集合"""
    db = await get_database()
    collection_name = os.getenv("MONGODB_CHAT_COLLECTION", "deepsearch_agent")
    return db[collection_name]


async def close_mongodb_connection():
    """关闭MongoDB连接（应用 shutdown 时调用）"""
    global _async_client, _database
    if _async_client:
        _async_client.close()
        _async_client = None
        _database = None
        print("[INFO] MongoDB connection closed")


async def init_mongodb_indexes():
    """初始化MongoDB索引（应用启动时调用）"""
    try:
        collection = await get_chat_collection()

        # 1. 复合索引：快速查询用户的会话列表
        await collection.create_index(
            [("user_id", 1), ("session_id", 1), ("created_at", -1)],
            name="idx_user_session_time"
        )

        # 2. 会话ID索引：快速定位特定会话
        await collection.create_index(
            [("session_id", 1), ("message_index", 1)],
            name="idx_session_messages",
            unique=False
        )

        # 3. TTL索引：自动清理过期数据（30天）
        ttl_days = int(os.getenv("MONGODB_MEMORY_TTL_DAYS", "30"))
        await collection.create_index(
            [("created_at", 1)],
            expireAfterSeconds=ttl_days * 86400,
            name="idx_ttl_cleanup"
        )

        # 4. 用户ID索引：统计用户使用情况
        await collection.create_index(
            [("user_id", 1)],
            name="idx_user_id"
        )

        print(f"[INFO] MongoDB indexes initialized successfully (TTL={ttl_days} days)")
    except Exception as e:
        print(f"[WARNING] MongoDB index initialization failed: {e}")
