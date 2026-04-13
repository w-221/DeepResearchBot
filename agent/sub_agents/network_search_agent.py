from agent.prompts import sub_agents_config
from tools.baidu_search_tools import internet_search

network_search_agent = {
    "name": sub_agents_config["baidu"].get("name", "网络搜索助手"),
    "description": sub_agents_config["baidu"].get("description", "负责进行网络知识搜索的智能体助手"),
    "system_prompt": sub_agents_config["baidu"].get("system_prompt", ""),
    "tools": [internet_search]
}