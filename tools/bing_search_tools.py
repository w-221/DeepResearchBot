# ======================== 导入核心依赖 ========================
# 类型注解：增强代码提示和静态检查能力
from typing import Literal
# LangChain 工具装饰器：将普通函数转为 Agent 可调用的工具
from langchain_core.tools import tool
# LangChain Bing Search API 封装
from langchain_community.utilities import BingSearchAPIWrapper

# 系统/第三方依赖
import os  # 系统路径/环境变量处理
from dotenv import load_dotenv  # 加载 .env 文件中的环境变量

# 自定义模块：工具调用埋点监控（需确保 api 模块可导入）
from api.monitor import monitor

# ======================== 初始化配置 ========================
# 加载项目根目录的 .env 文件，读取环境变量（如 BING_API_KEY）
load_dotenv()

# 初始化 Bing Search API 客户端
bing_api_key = os.getenv("BING_API_KEY")
bing_subscription_key = os.getenv("BING_SUBSCRIPTION_KEY", bing_api_key)

if bing_subscription_key:
    try:
        search_wrapper = BingSearchAPIWrapper(
            bing_search_url="https://api.bing.microsoft.com/v7.0/search",
            bing_subscription_key=bing_subscription_key,
            k=5  # 默认返回结果数量
        )
    except Exception as e:
        print(f"[WARNING] Bing Search API 初始化失败: {e}")
        search_wrapper = None
else:
    print("[WARNING] 未找到 BING_API_KEY 或 BING_SUBSCRIPTION_KEY 环境变量")
    search_wrapper = None


# 定义网络搜索工具
@tool
def internet_search(
        query: str,
        max_results: int = 5,
        include_snippets: bool = True
):
    """
    根据问题进行网络查询，当需要获取外部互联网的公开信息、最新新闻或特定主题数据时使用此工具

    核心用途：
        当 AI Agent 需要获取外部互联网的公开信息、时效性数据（如新闻、金融动态）时调用，
        使用 Bing 搜索引擎返回结构化结果。

    参数说明：
        query: 搜索的核心问题/关键词，例如 "2026年AI行业政策"
        max_results: 控制返回结果数量，建议不超过10
        include_snippets: 是否包含搜索摘要，True返回摘要信息

    返回值：
        list: 搜索结果列表，每个元素包含以下字段：
            - title: 网页标题
            - link: 网页链接
            - snippet: 网页摘要（如果 include_snippets 为 True）
        str: 初始化失败时返回错误提示字符串

    异常处理：
        捕获搜索过程中的所有异常并返回错误信息，确保 Agent 能感知到搜索失败
    """
    if not search_wrapper:
        return "Error: Bing Search API 未初始化，请检查 BING_API_KEY 或 BING_SUBSCRIPTION_KEY 环境变量。"

    monitor.report_tool("网络搜索工具", {"网络搜索工具": query})

    try:
        # 使用 Bing Search API 进行搜索
        results = search_wrapper.results(
            query=query,
            num_results=max_results
        )

        # 如果 include_snippets 为 False，只返回标题和链接
        if not include_snippets and isinstance(results, list):
            return [
                {
                    "title": result.get("title", ""),
                    "link": result.get("link", "")
                }
                for result in results
            ]

        return results

    except Exception as e:
        error_msg = f"Bing Search 查询失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return error_msg