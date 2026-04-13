# 导入系统核心模块
import os
import logging
from typing import List, Optional, Tuple
from typing_extensions import Annotated

# 导入 LangChain 工具装饰器
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入监控模块
from api.monitor import monitor

# 导入环境变量加载
from dotenv import load_dotenv

# 导入上下文模块，用于获取会话目录
from api.context import get_session_context

# 初始化日志器
logger = logging.getLogger(__name__)

# 全局变量：向量数据库实例
_vector_store = None
_embeddings = None


def _get_embeddings():
    """获取嵌入模型实例（支持本地和 API 两种方式）"""
    global _embeddings

    if _embeddings is not None:
        return _embeddings

    load_dotenv()

    # 方案1: 尝试使用通义千问的嵌入模型
    try:
        from langchain_community.embeddings import DashScopeEmbeddings

        api_key = os.getenv("OPENAI_API_KEY")
        embedding_model = os.getenv("LLM_TEXT_EMBEDDING", "text-embedding-v4")

        if api_key:
            _embeddings = DashScopeEmbeddings(
                model=embedding_model,
                dashscope_api_key=api_key
            )
            logger.info(f"使用 DashScope Embeddings (模型: {embedding_model})")
            return _embeddings
    except ImportError as e:
        logger.warning(f"DashScope 模块未安装: {e}")
    except Exception as e:
        logger.warning(f"DashScope Embeddings 加载失败: {e}")

    # 方案2: 回退到本地模型（使用新的 langchain_huggingface 包）
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        # 设置超时，避免长时间等待 HuggingFace 连接
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # 检查网络连接（超时 5 秒）
        try:
            requests.head("https://huggingface.co", timeout=5)
        except requests.exceptions.RequestException:
            logger.warning("无法连接 HuggingFace，跳过本地模型下载")
            raise Exception("HuggingFace 网络不可达")

        _embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",  # 轻量级中文模型
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        logger.info("使用 HuggingFace Embeddings (bge-small-zh-v1.5)")
        return _embeddings
    except ImportError as e:
        logger.warning(f"langchain_huggingface 模块未安装: {e}")
    except Exception as e:
        logger.warning(f"HuggingFace Embeddings 加载失败: {e}")

    # 方案3: 最后回退到 OpenAI 兼容格式（使用通义千问 API）
    try:
        from langchain_openai import OpenAIEmbeddings

        base_url = os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise Exception("未配置 OPENAI_API_KEY")

        _embeddings = OpenAIEmbeddings(
            base_url=base_url,
            api_key=api_key,
            model="text-embedding-v3"  # 通义千问支持的嵌入模型
        )
        logger.info(f"使用 OpenAI Embeddings (base_url: {base_url})")
        return _embeddings
    except Exception as e:
        logger.error(f"所有 Embeddings 加载失败: {e}")
        raise Exception(
            "无法加载任何嵌入模型。\n"
            "请选择以下方案之一：\n"
            "1. 安装 dashscope: pip install dashscope\n"
            "2. 安装 langchain-huggingface: pip install langchain-huggingface\n"
            "3. 确保 .env 文件中配置了 OPENAI_API_KEY"
        )


def _get_vector_store(persist_directory: str = None):
    """获取或创建向量数据库实例"""
    global _vector_store

    if _vector_store is not None and persist_directory is None:
        return _vector_store

    from langchain_chroma import Chroma

    embeddings = _get_embeddings()

    if persist_directory:
        # 持久化存储
        _vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name="knowledge_base"
        )
    else:
        # 内存存储
        _vector_store = Chroma(
            embedding_function=embeddings,
            collection_name="knowledge_base"
        )

    return _vector_store


def get_persist_dir() -> str:
    """获取知识库持久化目录"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persist_dir = os.path.join(project_root, "data", "chroma_db")
    os.makedirs(persist_dir, exist_ok=True)
    return persist_dir


@tool
def add_documents_to_kb(
    files_content: Annotated[str, "要添加到知识库的文档内容（可以是多个文档，用 ### 分隔）"],
) -> str:
    """
    【工具功能】将文档内容添加到本地知识库
    适用场景：需要为知识库添加新的文档资料
    注意：文档会被自动分块并转换为向量存储
    """
    monitor.report_tool("添加文档到知识库")

    try:
        vector_store = _get_vector_store(get_persist_dir())

        # 按分隔符分割多个文档
        documents = []
        for doc_content in files_content.split("###"):
            doc_content = doc_content.strip()
            if not doc_content:
                continue

            documents.append(Document(page_content=doc_content, metadata={"source": "manual_add"}))

        if not documents:
            return "错误：未提供有效的文档内容"

        # 文本分块
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
        )

        chunks = text_splitter.split_documents(documents)

        # 添加到向量库
        vector_store.add_documents(chunks)

        return f"成功添加 {len(documents)} 个文档，共 {len(chunks)} 个文本块到知识库"

    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        return f"添加文档失败: {str(e)}"


@tool
def list_session_files(
    dummy_arg: Annotated[str, "不需要输入参数，直接调用即可"] = "",
) -> str:
    """
    【工具功能】列出当前会话目录下的所有文件
    适用场景：
    1. 用户说"把我上传的文件..."时，先调用此工具查看有哪些文件
    2. 用户不确定上传了哪些文件时
    3. 需要了解会话目录中有哪些可用文件时

    返回：文件列表，包含文件名和文件大小
    注意：此工具会扫描 updated/session_{thread_id}/ 目录
    """
    monitor.report_tool("列出会话文件")

    try:
        session_dir = get_session_context()

        if not session_dir or not os.path.exists(session_dir):
            return f"会话目录不存在: {session_dir}"

        # 获取目录下所有文件
        files = []
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                # 格式化文件大小
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.2f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.2f} MB"
                files.append(f"- {filename} ({size_str})")

        if not files:
            return "会话目录中没有找到任何文件。"

        result = f"会话目录 ({session_dir}) 中的文件列表:\n"
        result += "\n".join(files)
        return result

    except Exception as e:
        logger.error(f"列出会话文件失败: {e}")
        return f"列出会话文件失败: {str(e)}"


@tool
def add_file_to_kb(
    file_path: Annotated[str, "要添加到知识库的文件路径。支持相对路径（如：policy.md）或绝对路径（如：D:/docs/policy.md）。支持 .txt, .md, .pdf 格式"],
) -> str:
    """
    【工具功能】将文件添加到知识库（向量化存储）
    适用场景：
    1. 用户上传文件后，在提示词中明确要求把上传的文件加入知识库
       示例：用户输入 "把我刚才上传的 policy.md 加入知识库"
    2. 用户指定服务器上的其他文件路径
       示例：用户输入 "把 D:/docs/company.txt 加入知识库"

    路径说明：
    - 支持相对路径（相对于会话上传目录 updated/session_{thread_id}/）
      例如：用户上传了 "faq.pdf"，可直接传 "faq.pdf"
    - 支持绝对路径（任意位置的文件）
      例如：D:/docs/policy.md、/home/user/docs/faq.pdf

    注意：
    - 当用户说"把我上传的文件..."等模糊表述时，应先调用 list_session_files 查看有哪些文件
    - 支持的文件格式：.txt、.md、.pdf
    """
    monitor.report_tool("添加文件到知识库", {"文件路径": file_path})

    # 添加调试日志
    print(f"[DEBUG add_file_to_kb] 输入路径: {file_path}")
    print(f"[DEBUG add_file_to_kb] 是否绝对路径: {os.path.isabs(file_path)}")

    try:
        # 解析文件路径：支持相对路径（从会话目录查找）和绝对路径
        actual_file_path = file_path

        # 判断是否是相对路径（不是绝对路径）
        # Windows 绝对路径: C:\, D:\ 等
        # Linux 绝对路径: / 开头
        is_relative_path = not (
            os.path.isabs(file_path) or
            (len(file_path) > 1 and file_path[1] == ':' and file_path[0].isalpha())  # Windows 盘符
        )

        print(f"[DEBUG add_file_to_kb] 是否相对路径: {is_relative_path}")

        if is_relative_path:
            # 相对路径：从会话目录查找
            session_dir = get_session_context()
            print(f"[DEBUG add_file_to_kb] 会话目录: {session_dir}")

            if session_dir and os.path.exists(session_dir):
                potential_path = os.path.join(session_dir, file_path)
                print(f"[DEBUG add_file_to_kb] 潜在路径: {potential_path}, 存在: {os.path.exists(potential_path)}")

                if os.path.exists(potential_path):
                    actual_file_path = potential_path
                    logger.info(f"从会话目录找到文件: {actual_file_path}")
                else:
                    return f"错误：在会话目录中未找到文件 '{file_path}'（会话目录：{session_dir}）"
            else:
                return f"错误：无法获取会话目录，请检查是否已启动会话"
        else:
            print(f"[DEBUG add_file_to_kb] 使用绝对路径: {actual_file_path}")

        if not os.path.exists(actual_file_path):
            return f"错误：文件不存在 - {file_path}"

        # 读取文件内容
        content = ""
        file_ext = os.path.splitext(actual_file_path)[1].lower()

        if file_ext in ['.txt', '.md']:
            with open(actual_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif file_ext == '.pdf':
            try:
                import pypdf
                pdf_reader = pypdf.PdfReader(actual_file_path)
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            except ImportError:
                return "错误：PDF 处理需要安装 pypdf 库（pip install pypdf）"
        else:
            return f"错误：不支持的文件格式 {file_ext}"

        if not content.strip():
            return "错误：文件内容为空"

        # 添加到向量库
        vector_store = _get_vector_store(get_persist_dir())

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
        )

        chunks = text_splitter.split_documents([
            Document(page_content=content, metadata={"source": file_path})
        ])

        vector_store.add_documents(chunks)

        return f"成功添加文件到知识库，共 {len(chunks)} 个文本块"

    except Exception as e:
        logger.error(f"添加文件失败: {e}")
        return f"添加文件失败: {str(e)}"


@tool
def search_knowledge_base(
    query: Annotated[str, "要查询的问题或关键词"],
    top_k: Annotated[int, "返回最相关的文档数量，默认 3"] = 3,
) -> str:
    """
    【工具功能】在本地知识库中搜索相关文档
    适用场景：需要根据用户问题检索知识库中的相关内容
    返回：最相关的文档片段及来源信息
    """
    monitor.report_tool("知识库搜索", {"查询": query, "返回数量": top_k})

    try:
        vector_store = _get_vector_store(get_persist_dir())

        # 相似度搜索
        results = vector_store.similarity_search_with_score(query, k=top_k)

        if not results:
            return "知识库中没有找到相关内容"

        # 格式化结果
        output_lines = []
        for doc, score in results:
            similarity = 1 - score  # 转换为相似度（分数越小越相似）
            source = doc.metadata.get("source", "未知来源")
            content = doc.page_content

            output_lines.append(f"【相似度: {similarity:.2f}】来源: {source}")
            output_lines.append(f"内容: {content}")
            output_lines.append("---")

        return "\n".join(output_lines)

    except Exception as e:
        logger.error(f"知识库搜索失败: {e}")
        return f"知识库搜索失败: {str(e)}"


@tool
def get_kb_status(
    dummy_arg: Annotated[str, "不需要输入参数，直接调用即可"] = "",
) -> str:
    """
    【工具功能】获取知识库状态信息
    适用场景：需要了解当前知识库中有多少文档和数据块
    """
    monitor.report_tool("查询知识库状态")

    try:
        vector_store = _get_vector_store(get_persist_dir())

        # 获取集合信息
        collection = vector_store._collection

        doc_count = collection.count()
        return f"知识库状态：当前共有 {doc_count} 个文档向量块"

    except Exception as e:
        logger.error(f"查询知识库状态失败: {e}")
        return f"查询知识库状态失败: {str(e)}"


@tool
def clear_knowledge_base(
    confirm: Annotated[str, "输入 'yes' 确认清空，否则取消操作"] = "",
) -> str:
    """
    【工具功能】清空知识库中的所有文档
    警告：此操作不可逆，会删除所有已存储的文档
    """
    if confirm.lower() != 'yes':
        return "操作已取消：清空知识库需要确认参数为 'yes'"

    monitor.report_tool("清空知识库")

    try:
        # 删除持久化目录
        persist_dir = get_persist_dir()
        import shutil
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
            os.makedirs(persist_dir, exist_ok=True)

        # 重置全局变量
        global _vector_store
        _vector_store = None

        return "知识库已清空，可以重新添加文档"

    except Exception as e:
        logger.error(f"清空知识库失败: {e}")
        return f"清空知识库失败: {str(e)}"


# 用于 LangChain 的 Retriever 接口
def get_knowledge_retriever(search_kwargs: dict = None):
    """
    获取知识库检索器（用于直接集成到 RAG Chain）

    Args:
        search_kwargs: 搜索参数，如 {"k": 3}

    Returns:
        LangChain Retriever 对象
    """
    vector_store = _get_vector_store(get_persist_dir())
    return vector_store.as_retriever(search_kwargs=search_kwargs or {"k": 3})


# 初始化时加载（可选）
def init_knowledge_base():
    """初始化知识库，确保向量数据库可用"""
    try:
        _get_vector_store(get_persist_dir())
        logger.info("知识库初始化成功")
    except Exception as e:
        logger.error(f"知识库初始化失败: {e}")


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    print("初始化知识库...")
    init_knowledge_base()

    print("\n当前状态:")
    print(get_kb_status())

    print("\n添加测试文档...")
    result = add_documents_to_kb("### 测试文档1\n这是一个测试文档，用于验证 RAG 系统是否正常工作。")
    print(result)

    print("\n当前状态:")
    print(get_kb_status())

    print("\n搜索测试...")
    print(search_knowledge_base("测试文档"))