from app.core.agent_base import BaseAgent


SUGGESTION_SYSTEM_PROMPT = """你是一个资深的合同修改专家，擅长把有风险的条款修改得合法、严谨、公平。

你的任务是针对合同条款的风险点，给出具体的修改建议和修改后的条款文本。

请严格按 JSON 格式输出，不要输出其他内容：
{
  "suggestions": [
    {
      "original_text": "原条款中需要修改的原文",
      "suggested_text": "修改后的文本",
      "修改理由": "为什么这样改",
      "modification_type": "删除/修改/增加/替换"
    }
  ],
  "revised_clause": "修改后的完整条款（如果需要整体重写）",
  "explanation": "修改说明"
}

修改原则：
1. 保持商业意图不变，只修正法律风险
2. 修改后的条款要严谨、明确、可执行
3. 尽量平衡双方权利义务
4. 使用规范的法律用语
5. 如果条款整体有问题，给出完整重写版本
"""


class SuggestionAgent(BaseAgent):
    """修改建议 Agent：给出条款修改建议"""
    
    def __init__(self):
        super().__init__(
            name="修改建议Agent",
            system_prompt=SUGGESTION_SYSTEM_PROMPT,
            temperature=0.4
        )
    
    def analyze(self, clause_title: str, clause_content: str, risk_analysis: dict, compliance_analysis: dict) -> dict:
        """根据风险和合规分析，给出修改建议"""
        user_input = f"""【条款标题】{clause_title}

【条款原文】{clause_content}

【风险分析结果】
{risk_analysis}

【合规分析结果】
{compliance_analysis}

请根据以上分析，给出具体的修改建议，输出 JSON 格式结果。"""
        
        return self.run_json(user_input)
