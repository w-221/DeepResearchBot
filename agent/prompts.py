import yaml
from pathlib import Path


# 加载YAML格式的提示词配置文件
def load_prompt(file_path):
    """
    读取并加载YAML格式的提示词配置文件
    Args:
        file_path (str/Path): YAML配置文件的路径
    Returns:
        dict: 解析后的YAML配置字典，包含主智能体和子智能体的提示词配置
    """
    # 以UTF-8编码打开文件，避免中文乱码，参数'r'表示以只读模式打开文件
    with open(file_path, 'r', encoding="utf-8") as f:
        """
        这是 safe_load 区别于 load 的核心（也是为什么必须用它）：
        yaml.load()：不安全，会解析 YAML 中的「自定义对象 / 执行代码」，如果加载的 YAML 文件被恶意篡改（比如插入了执行系统命令的代码），会导致服务器被攻击、数据泄露；
        yaml.safe_load()：仅解析 YAML 标准数据类型（字符串、数字、字典、列表、布尔值等），完全禁止解析 / 执行任何自定义对象、函数、代码，从根源避免安全风险。
        """
        # 使用safe_load保证加载安全，将yaml文件内容解析为Python字典并返回
        return yaml.safe_load(f)


# 获取当前脚本文件的父级目录的上一级（项目根目录）
# Path(__file__)：当前脚本文件的绝对路径
# parents[1]：向上追溯两级目录，定位到项目根目录
root_path = Path(__file__).parents[1]

# 拼接提示词配置文件的完整路径（根目录/prompt/prompts.yml）
prompt_file_path = root_path / "prompt" / "prompts.yaml"

# 加载YAML配置文件内容，返回解析后的字典prompt_config_content
prompt_config_content = load_prompt(prompt_file_path)
# 打印完整配置内容，用于调试验证加载是否成功
print(f"prompt_config_content: {prompt_config_content}")

# 从总配置中提取主智能体的配置（对应prompts.yml中的main_agent节点）
main_agent_config = prompt_config_content["main_agent"]
# 从总配置中提取子智能体的配置（对应prompts.yml中的sub_agents节点）
sub_agents_config = prompt_config_content["sub_agents"]

# 打印拆分后的配置，验证核心配置节点是否正确提取
print(f"main_agent_config: {main_agent_config} , \nsub_agents_config: {sub_agents_config}")