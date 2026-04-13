import os
import json
import logging
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


class AgentLogger:
    """
    Agent 日志记录核心类 (基于标准 logging 模块封装)。

    设计目的：
    1. **解耦 (Decoupling)**：将日志写入逻辑与 Agent 的业务逻辑分离。
    2. **多层级记录 (Multi-level Logging)**：
       - 高层级：记录主智能体 (Main Agent) 的状态流转。
       - 低层级：通过 Callback 机制捕获子智能体 (Sub Agent) 的细节。
    3. **会话隔离 (Session Isolation)**：基于 thread_id 生成独立日志文件。
    4. **标准库支持**：使用 logging 模块实现线程安全的文件写入和格式化。
    """

    def __init__(self, thread_id: str, project_root: str):
        """
        初始化日志记录器。

        Args:
            thread_id: 当前任务的唯一会话 ID。
            project_root: 项目根目录。
        """
        self.thread_id = thread_id
        self.log_dir = os.path.join(project_root, "log")
        self.log_file = os.path.join(self.log_dir, f"agent_trace_{thread_id}.log")

        self._ensure_log_dir()

        # 初始化标准 logger
        self.logger = self._setup_logger()

        # 写入初始化日志头
        self._write_log("SYSTEM", f"Logger initialized for thread: {thread_id}")

    def _ensure_log_dir(self):
        """检查并创建日志目录。"""
        try:
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)
        except Exception as e:
            print(f"[AgentLogger] Warning: Failed to create log directory: {e}")

    def _setup_logger(self) -> logging.Logger:
        """配置并获取标准 Logger 实例"""
        # 使用 thread_id 作为 logger name，保证唯一性
        logger_name = f"agent_trace_{self.thread_id}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # 防止重复添加 Handler (如果 Logger 已存在)
        if not logger.handlers:
            try:
                # 创建 FileHandler，使用 utf-8 编码
                file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                file_handler.setLevel(logging.INFO)

                # 自定义 Formatter
                # 格式: [时间] [消息]
                # 注意：具体的 category 和 content 结构我们会在 _write_log 中拼装
                formatter = logging.Formatter(
                    fmt='[%(asctime)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(formatter)

                logger.addHandler(file_handler)
            except Exception as e:
                print(f"[AgentLogger] Error setting up logger: {e}")

        return logger

    def _write_log(self, category: str, content: str):
        """
        底层写入方法：委托给标准 logger。

        Args:
            category: 日志类别。
            content: 具体日志内容。
        """
        # 拼装符合原格式的消息体
        # 注意：logging 自动添加的时间戳在最前面
        # 最终输出形如：[2023-XX-XX XX:XX:XX] [CATEGORY]
        # Content
        # ----------------------------------------
        formatted_message = f"[{category}]\n{content}\n{'-' * 40}"
        self.logger.info(formatted_message)

    def log_main_chunk(self, chunk: Any):
        """
        [高层级] 记录主智能体的状态更新 (LangGraph State Update)。
        这是在 Agent 循环中显式调用的。
        """
        self._write_log("MAIN_AGENT_STATE_UPDATE", str(chunk))

    def log_tool_call(self, tool_name: str, args: Dict[str, Any]):
        """
        [高层级] 记录主智能体工具调用的参数细节。
        """
        try:
            # 尝试格式化 JSON 以便阅读
            args_str = json.dumps(args, ensure_ascii=False, indent=2)
        except:
            args_str = str(args)

        content = f"Tool Name: {tool_name}\nArguments:\n{args_str}"
        self._write_log("TOOL_CALL_DETAILS", content)


class AgentLogCallbackHandler(BaseCallbackHandler):
    """
    [低层级] LangChain 回调处理器。

    作用：
    当 LangChain/LangGraph 内部运行时（例如 LLM 正在生成 Token，或者 Tool 正在执行），
    它会自动触发这些钩子函数 (Hooks)。

    这使我们能够“窥探”到 Agent 内部的黑盒操作，特别是子智能体的思考过程。
    如果没有这个 Handler，我们只能看到 Agent 的最终结果，看不到中间的思考过程。
    """

    def __init__(self, logger: AgentLogger):
        # 持有 AgentLogger 实例，以便将捕获到的信息写入文件
        self.logger = logger

    def on_llm_start(
            self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        """
        钩子：当 LLM 开始生成时触发。
        用于记录发送给 LLM 的 Prompt 是什么（便于调试 Prompt 工程）。
        """
        tags = kwargs.get("tags", [])
        # 只记录第一个 prompt 的前 1000 个字符，避免日志爆炸
        prompt_preview = prompts[0][:1000] + "..." if prompts else "No prompts"
        self.logger._write_log("LLM_START", f"Tags: {tags}\nPrompts Preview:\n{prompt_preview}")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any:
        """
        钩子：当 LLM 生成每一个 Token 时触发 (流式输出)。
        用于捕获子智能体实时的打字效果。
        """
        # 只有非空字符才记录，减少 I/O 压力
        if token:
            # 注意：频繁写入文件会影响性能，生产环境通常使用内存 Buffer 缓冲写入
            # 这里为了演示清晰，直接写入
            self.logger._write_log("LLM_TOKEN_CHUNK", token)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """
        钩子：当 LLM 生成结束时触发。
        记录完整的生成结果。
        """
        generations = response.generations
        for gen_list in generations:
            for gen in gen_list:
                self.logger._write_log("LLM_OUTPUT", gen.text)

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        """
        钩子：当任何 Tool 开始执行时触发。
        捕获工具名称和原始输入字符串。
        """
        name = serialized.get("name", "unknown")
        self.logger._write_log("TOOL_START", f"Tool: {name}\nInput: {input_str}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        """
        钩子：当 Tool 执行完毕时触发。
        捕获工具的返回结果。
        """
        # 处理不同类型的 output（可能是 ToolMessage 对象、字符串或其他类型）
        if hasattr(output, 'content'):
            output_str = str(output.content)
        else:
            output_str = str(output)

        # 截断过长的工具输出，防止日志文件过大（例如读取了整个 PDF 内容）
        preview = output_str[:2000] + "..." if len(output_str) > 2000 else output_str
        self.logger._write_log("TOOL_END", f"Output: {preview}")

    def on_chain_start(
            self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> Any:
        """
        钩子：当 Chain (Agent 内部的一个执行链) 开始时触发。
        """
        name = serialized.get("name", "unknown") if serialized else "unknown"
        tags = kwargs.get("tags", [])
        # 过滤掉内部琐碎的 Chain，只记录关键步骤
        if tags and "seq:step" not in tags:
            self.logger._write_log("CHAIN_START", f"Chain: {name}\nTags: {tags}\nInputs: {str(inputs)[:500]}...")