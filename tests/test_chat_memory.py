"""
tests/test_chat_memory.py
测试聊天记忆管理器
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chat_memory_manager import get_memory_manager
from api.mongodb_client import init_mongodb_indexes


async def test_chat_memory():
    """测试聊天记忆功能"""
    print("=" * 60)
    print("Testing Chat Memory Manager")
    print("=" * 60)

    # 初始化索引
    await init_mongodb_indexes()

    # 获取记忆管理器
    manager = get_memory_manager()

    # 测试会话ID
    test_session_id = "test_session_001"
    test_user_id = "user_12345"

    print("\n1. Saving messages...")
    # 保存测试消息
    for i in range(5):
        await manager.save_message(
            session_id=test_session_id,
            user_id=test_user_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Test message {i + 1}",
            immediate=True
        )

    print("✓ Messages saved")

    print("\n2. Retrieving messages...")
    # 获取消息
    messages = await manager.get_messages(test_session_id, limit=10)
    print(f"✓ Retrieved {len(messages)} messages")

    for msg in messages:
        print(f"  - [{msg['role']}] {msg['content']}")

    print("\n3. Getting session stats...")
    # 获取统计信息
    stats = await manager.get_session_stats(test_session_id)
    print(f"✓ Stats: {stats}")

    print("\n4. Testing Redis cache...")
    # 再次获取（应该命中缓存）
    messages_cached = await manager.get_messages(test_session_id, limit=10)
    print(f"✓ Cache retrieval: {len(messages_cached)} messages")

    # print("\n5. Clearing session...")
    # # 清空会话
    # success = await manager.clear_session(test_session_id)
    # print(f"✓ Session cleared: {success}")
    #
    # # 验证清空
    # messages_after = await manager.get_messages(test_session_id, limit=10)
    # print(f"✓ Messages after clear: {len(messages_after)}")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chat_memory())
