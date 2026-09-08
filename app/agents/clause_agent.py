from app.core.agent_base import BaseAgent


CLAUSE_SYSTEM_PROMPT = """你是一个专业的合同条款分析专家。

你的任务是分析合同条款，识别每个条款的类型和关键信息。

请严格按 JSON 格式输出，不要输出其他内容：
{
  "clause_type": "条款类型（如：标的、数量质量、价款支付、履行交付、验收、违约责任、争议解决、不可抗力、其他）",
  "key_points": ["关键点1", "关键点2"],
  "summary": "一句话总结这个条款的内容"
}

条款类型只能从以下选项中选择：
- 标的
- 数量质量
- 价款支付
- 履行交付
- 验收
- 违约责任
- 争议解决
- 不可抗力
- 合同变更
- 其他
"""


class ClauseAgent(BaseAgent):
    """条款抽取 Agent：识别条款类型和关键信息"""
    
    def __init__(self):
        super().__init__(
            name="条款抽取Agent",
            system_prompt=CLAUSE_SYSTEM_PROMPT,
            temperature=0.1
        )
    
    def analyze(self, clause_title: str, clause_content: str) -> dict:
        """分析单个条款"""
        user_input = f"""请分析以下合同条款：

【条款标题】{clause_title}

【条款内容】{clause_content}

请输出 JSON 格式的分析结果。"""
        
        return self.run_json(user_input)
