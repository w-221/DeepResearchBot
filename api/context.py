from contextvars import ContextVar
from typing import Optional

# =========================================================================================
# 核心知识点: ContextVars (上下文变量)
# =========================================================================================
# Q: 为什么我们需要 ContextVar？为什么不能直接用全局变量？
#
# A: 在开发异步 Web 服务 (如 FastAPI) 时，系统是 "并发" 处理多个用户请求的。
#    但在 Python 的 asyncio 机制下，这些并发请求通常运行在 *同一个线程 (Thread)* 中。
#
#    1. 如果使用全局变量 (Global Variable):
#       当 User A 的请求正在处理时，User B 的请求进来了。如果修改了全局变量，User A 的数据
#       就会被 User B 覆盖，导致严重的 "串台" 事故（例如 User A 的文件存到了 User B 的目录）。
#
#    2. 如果使用 threading.local:
#       它是基于线程隔离的。因为 asyncio 所有协程都在同一个线程跑，所以 threading.local
#       在异步场景下失效，无法隔离不同用户的请求。
#
#    3. ContextVar 的解决方案:
#       ContextVar 是 Python 3.7+ 专门为异步编程设计的 "协程级局部变量"。
#       它能确保变量在每一个 asyncio Task (即每个用户请求) 中是 *独立隔离* 的。
#       无论代码调用多深，只要是在同一个请求链路（Context）中，get() 到的都是属于当前请求的数据。
# =========================================================================================
# 定义 ContextVar 上下文变量
# -------------------------------------------------------------------------
# 这里的变量名只是一个标识符 (Identifier)，真正的值是存储在当前的 Context 环境中的。

# 存储当前会话对应的文件夹
# 这是Python的变量类型注解，用于静态类型检查，告诉解释器这是一个ContextVar对象，存储类型为Optional[str]
_session_dir_ctx: ContextVar[Optional[str]] = ContextVar("session_dir", default=None)

# 存储当前会话对应的websocket
_thread_id_ctx: ContextVar[Optional[str]] = ContextVar("thread_id", default=None)

'''
_session_dir_ctx用来存储会话对应的文件夹的位置，这样不同会话产生的文件就会存储在各自的目录下，不会混在一起
_thread_id_ctx用来存储会话的线程id
这两个ContextVar对象起到协程之间数据共享的作用，一个协程可以在里面存入数据，另一个协程可以取出数据
'''

def set_session_context(path: str):
    """
    设置当前请求链路的会话的请求路径。
    通常在 Agent 开始执行任务前调用。

    Returns:
        Token: ContextVar调用set函数就会返回一个 Token 对象，后续可用它来恢复(reset)变量状态。
    """
    return _session_dir_ctx.set(path)


def get_session_context() -> Optional[str]:
    """
    获取当前请求链路的会话目录。
    可以在任何深层调用的工具函数中直接使用，无需层层传递参数。
    """
    return _session_dir_ctx.get()


def set_thread_context(thread_id: str):
    """
    设置当前请求链路的 Thread ID。
    """
    return _thread_id_ctx.set(thread_id)


def get_thread_context() -> Optional[str]:
    """
    获取当前请求链路的 Thread ID。
    """
    return _thread_id_ctx.get()


def reset_session_context(session_token, thread_token=None):
    """
    清理/重置上下文。
    通常在请求处理结束 (finally 块) 中调用，防止内存泄漏或污染后续请求。
    session_token：从 set_session_context 返回的 Token。
    thread_token：可选，从 set_thread_context 返回的 Token。
    """
    _session_dir_ctx.reset(session_token)
    if thread_token:
        _thread_id_ctx.reset(thread_token)


if __name__ == "__main__":
    import asyncio
    import random


    # =========================================================================
    # 模拟案例：张三和李四同时来办理业务
    # =========================================================================
    async def process_user_request(user_name: str, user_dir: str):
        print(f"[{user_name}] 1. 请求开始，设置环境 -> {user_dir}")

        # 1. 【进门】设置上下文，拿到凭证 (Token)
        #    注意：这里不需要把 token 传给 deep_function，它自己能取到 context
        dir_token = set_session_context(user_dir)
        id_token = set_thread_context(f"thread_{user_name}")

        try:
            # 2. 【办事】模拟进入深层函数调用 (中间可能隔了十层八层)
            await deep_nested_function(user_name)

        finally:
            # 3. 【出门】业务办完，必须拿着凭证销户 (恢复现场)
            print(f"[{user_name}] 4. 请求结束，清理环境")
            reset_session_context(dir_token, id_token)

            # 验证清理结果 (应该变回 None 或初始值)
            current_dir = get_session_context()
            print(f"[{user_name}] 5. 清理后检查: {current_dir} (应该是 None)")


    async def deep_nested_function(user_name):
        """
        这是一个深层调用的函数，它没有接收任何 path 参数。
        但它可以通过 ContextVar "隔空取物"。
        """
        # 模拟耗时操作，让张三和李四的任务交织在一起
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # 核心验证：直接从 Context 取值
        # 如果没有隔离，李四可能会取到张三的目录
        current_dir = get_session_context()
        current_thread = get_thread_context()

        print(f"[{user_name}] 2. 在深层函数中获取上下文:")
        print(f"    - 目录: {current_dir}")
        print(f"    - 线程: {current_thread}")

        if user_name in current_thread and user_name in current_dir:
            print(f"[{user_name}] 3. ✅ 验证成功！数据是正确的！")
        else:
            print(f"[{user_name}] 3. ❌ 验证失败！数据串台了！")


    async def main():
        print("--- 开始并发测试 ---\n")
        # 同时启动两个任务，模拟并发
        task1 = asyncio.create_task(process_user_request("张三", "/data/zhangsan"))
        task2 = asyncio.create_task(process_user_request("李四", "/data/lisi"))

        await asyncio.gather(task1, task2)
        print("\n--- 测试结束 ---")


    asyncio.run(main())