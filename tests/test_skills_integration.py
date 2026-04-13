# tests/test_skills_integration.py
"""测试Skills集成"""
import asyncio
from pathlib import Path
from agent.main_agent import main_agent


async def test_skills_loaded():
    """测试Skills是否正确加载"""
    print("🧪 测试 Skills 集成...")

    # 检查skills目录
    project_root = Path(__file__).parent.parent
    skills_dir = project_root / "skills"

    if not skills_dir.exists():
        print(f"❌ Skills目录不存在: {skills_dir}")
        return False

    # 列出可用的Skills
    available_skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
    print(f"✅ 发现 {len(available_skills)} 个Skills: {available_skills}")

    # 检查每个Skill是否有SKILL.md
    for skill_name in available_skills:
        skill_path = skills_dir / skill_name / "SKILL.md"
        if skill_path.exists():
            print(f"  ✅ {skill_name}: SKILL.md 存在")
        else:
            print(f"  ⚠️  {skill_name}: 缺少 SKILL.md")

    # 测试Agent是否能识别Skills
    try:
        result = await main_agent.ainvoke({
            "messages": [{
                "role": "user",
                "content": "帮我审查一下这个Python函数的安全性：\n\ndef login(username, password):\n    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n    return execute_query(query)"
            }]
        })

        print("\n✅ Agent响应成功")
        print(f"响应预览: {str(result)[:200]}...")
        return True

    except Exception as e:
        print(f"\n❌ Agent执行失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_skills_loaded())
    if success:
        print("\n🎉 Skills集成测试通过！")
    else:
        print("\n⚠️  Skills集成测试失败，请检查配置")
