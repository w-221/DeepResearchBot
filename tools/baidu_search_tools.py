# ======================== 导入核心依赖 ========================
# 类型注解：增强代码提示和静态检查能力
from typing import Literal
# LangChain 工具装饰器：将普通函数转为 Agent 可调用的工具
from langchain_core.tools import tool

# 系统/第三方依赖
import os  # 系统路径/环境变量处理
import json  # JSON 解析
import time  # 时间戳（用于 token 过期判断）
import requests  # HTTP 请求
from dotenv import load_dotenv  # 加载 .env 文件中的环境变量

# 自定义模块：工具调用埋点监控（需确保 api 模块可导入）
from api.monitor import monitor

# ======================== 初始化配置 ========================
# 加载项目根目录的 .env 文件，读取环境变量（如 BAIDU_API_KEY）
load_dotenv()

# 百度搜索 API 配置
BAIDU_API_KEY = os.getenv("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.getenv("BAIDU_SECRET_KEY", "")
# 默认使用百度千帆搜索接口
BAIDU_SEARCH_HOST = os.getenv("BAIDU_SEARCH_HOST", "https://qianfan.baidubce.com/v2/ai_search/web_search")

# 打印配置信息
print(f"[DEBUG] 百度搜索配置:")
print(f"  API Key: {'已设置' if BAIDU_API_KEY else '未设置'}")
print(f"  Secret Key: {'已设置' if BAIDU_SECRET_KEY else '未设置'}")
print(f"  接口地址: {BAIDU_SEARCH_HOST}")


def baidu_search_api_key(query: str, max_results: int = 5):
    """
    使用直接 API Key 认证模式调用百度搜索 API

    根据百度智能云提供的示例代码重写：
    - 使用 messages 数组格式
    - 在 Authorization 请求头中传递 Bearer token
    - 添加其他必要参数

    Args:
        query: 搜索关键词
        max_results: 返回结果数量

    Returns:
        dict: 搜索结果
    """
    print(f"[DEBUG] API Key 模式搜索: query={query}, max_results={max_results}")

    if not BAIDU_API_KEY:
        print("[ERROR] 未找到 BAIDU_API_KEY 环境变量")
        return {"error": "未找到 BAIDU_API_KEY 环境变量"}

    # 按照百度示例代码构造请求
    payload = json.dumps({
        "messages": [
            {
                "role": "user",
                "content": query
            }
        ],
        "edition": "standard",
        "search_source": "baidu_search_v2",
        "search_recency_filter": "week"
    }, ensure_ascii=False)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {BAIDU_API_KEY}'
    }

    print(f"[DEBUG] 请求 URL: {BAIDU_SEARCH_HOST}")
    print(f"[DEBUG] 请求头 Authorization: Bearer {BAIDU_API_KEY[:8]}...")
    print(f"[DEBUG] 请求参数: {payload[:200]}...")

    try:
        response = requests.request(
            "POST",
            BAIDU_SEARCH_HOST,
            headers=headers,
            data=payload.encode("utf-8"),
            timeout=30
        )

        print(f"[DEBUG] 响应状态码: {response.status_code}")
        print(f"[DEBUG] 响应头: {dict(response.headers)}")

        # 尝试解析 JSON
        response.encoding = "utf-8"
        try:
            result = response.json()
            print(f"[DEBUG] 响应内容: {json.dumps(result, ensure_ascii=False)[:500]}")

            # 检查是否有错误
            if isinstance(result, dict):
                if "error_code" in result and result["error_code"] != 0:
                    error_msg = f"百度 API 错误: {result.get('error_msg', '未知错误')} (错误码: {result['error_code']})"
                    print(f"[ERROR] {error_msg}")
                    return {"error": error_msg}
                if "error" in result:
                    error_msg = f"百度 API 错误: {result.get('error', '未知错误')}"
                    print(f"[ERROR] {error_msg}")
                    return {"error": error_msg}

            return result

        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON 解析失败: {e}")
            print(f"[DEBUG] 原始响应内容: {response.text[:500]}")
            return {"error": f"响应格式错误: {response.text[:200]}"}

    except requests.exceptions.Timeout:
        print("[ERROR] 百度搜索请求超时")
        return {"error": "百度搜索请求超时"}
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] 百度搜索连接失败: {e}")
        return {"error": f"百度搜索连接失败: {str(e)}"}
    except Exception as e:
        print(f"[ERROR] 百度搜索请求失败: {e}")
        return {"error": f"百度搜索请求失败: {str(e)}"}


# 定义网络搜索工具
@tool
def internet_search(
        query: str,
        max_results: int = 5
):
    """
    根据问题进行网络查询，当需要获取外部互联网的公开信息、最新新闻或特定主题数据时使用此工具

    核心用途：
        当 AI Agent 需要获取外部互联网的公开信息、时效性数据（如新闻、金融动态）时调用，
        使用百度搜索引擎返回结构化结果。

    参数说明：
        query: 搜索的核心问题/关键词，例如 "2026年AI行业政策"
        max_results: 控制返回结果数量，建议不超过10

    返回值：
        dict: 搜索结果，包含以下字段：
            - query: 原始搜索词
            - results: 搜索结果列表
            - answer: AI 生成的搜索摘要（AI 搜索模式）
        str: 初始化失败时返回错误提示字符串

    异常处理：
        捕获搜索过程中的所有异常并返回错误信息，确保 Agent 能感知到搜索失败
    """
    print(f"[DEBUG] internet_search 被调用: query={query}, max_results={max_results}")

    if not BAIDU_API_KEY:
        error_msg = "Error: 百度 API 未初始化，请检查 BAIDU_API_KEY 环境变量。"
        print(f"[ERROR] {error_msg}")
        return error_msg

    monitor.report_tool("网络搜索工具", {"网络搜索工具": query})

    try:
        # 添加延迟避免QPS限流
        time.sleep(2)
        # 调用百度搜索
        result = baidu_search_api_key(query, max_results)

        print(f"[DEBUG] 搜索结果类型: {type(result)}")

        # 格式化返回结果
        if isinstance(result, dict):
            if "error" in result:
                error_msg = f"搜索失败: {result['error']}"
                print(f"[ERROR] {error_msg}")
                return error_msg

            # 百度千帆搜索返回格式
            # 检查 result 字段（可能是直接结果）
            if "result" in result:
                print(f"[DEBUG] 解析 result 字段")
                return result

            # 检查 choices 字段（Chat 格式）
            if "choices" in result:
                print(f"[DEBUG] 解析 choices 字段")
                answer = result["choices"][0].get("message", {}).get("content", "")
                return {
                    "query": query,
                    "answer": answer,
                    "results": []
                }

            # 如果都不匹配，返回原始结果
            print(f"[DEBUG] 未匹配到已知格式，返回原始结果")
            return result

        # 如果返回的是字符串，直接返回
        elif isinstance(result, str):
            print(f"[DEBUG] 返回字符串结果")
            return result

        else:
            error_msg = f"搜索返回了未知类型: {type(result)}"
            print(f"[ERROR] {error_msg}")
            return error_msg

    except Exception as e:
        error_msg = f"百度搜索查询失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return error_msg


# ======================== 简易搜索接口（备用）========================
@tool
def simple_web_search(query: str, max_results: int = 5):
    """
    简易网页搜索工具（备用方案）
    使用 requests 直接抓取百度搜索结果页面
    注意：此方案不稳定，建议使用官方 API
    """
    monitor.report_tool("简易网络搜索工具", {"网络搜索工具": query})

    try:
        # 使用百度搜索 URL
        url = f"https://www.baidu.com/s"
        params = {
            "wd": query,
            "rn": max_results
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        # 解析 HTML 返回结果
        # 注意：这里需要使用 BeautifulSoup 或其他 HTML 解析库
        # 为简化，这里返回原始 HTML
        return {
            "query": query,
            "html": response.text[:5000],  # 返回前 5000 字符
            "note": "需要安装 beautifulsoup4 库进行完整解析"
        }

    except Exception as e:
        error_msg = f"简易搜索失败: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return error_msg