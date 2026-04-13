from agent.prompts import sub_agents_config
from tools.local_rag_tools import (
    get_kb_status,
    search_knowledge_base,
    add_file_to_kb,
    add_documents_to_kb,
    clear_knowledge_base
)

local_knowledge_base_agent = {
    "name": sub_agents_config.get("local_rag", {}).get("name", "知识库助手"),
    "description": sub_agents_config.get("local_rag", {}).get(
        "description",
        "负责查询和管理本地知识库。当用户需要搜索文档、获取知识库信息或管理知识库内容时调用此助手。"
    ),
    "system_prompt": sub_agents_config.get("local_rag", {}).get(
        "system_prompt",
        """你是知识库助手，负责处理用户与本地知识库的交互。

你的主要功能包括：
1. 搜索知识库：根据用户问题检索相关文档内容
2. 查询知识库状态：了解当前知识库中有多少文档
3. 添加文档到知识库：将新文件或文本内容加入知识库
4. 清空知识库：删除所有已存储的文档（需用户确认）

使用规则：
- 当用户询问文档、资料、知识相关问题时，使用 search_knowledge_base 工具
- 当用户想查看知识库状态时，使用 get_kb_status 工具
- 当用户想添加文档时，使用 add_file_to_kb 或 add_documents_to_kb 工具
- 清空知识库前，必须确认用户意图，因为此操作不可逆

回答时：
- 基于知识库检索结果回答问题
- 如果知识库中没有相关内容，诚实告知用户
- 引用具体来源信息，增加回答的可信度
"""
    ),
    "tools": [
        search_knowledge_base,
        get_kb_status,
        add_file_to_kb,
        add_documents_to_kb,
        clear_knowledge_base
    ]
}