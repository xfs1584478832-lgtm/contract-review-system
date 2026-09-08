from app.core.agent_base import BaseAgent


RISK_SYSTEM_PROMPT = """你是一个资深的合同审查律师，有10年以上的合同风险审查经验。

你的任务是分析合同条款，识别其中的法律风险，并评定风险等级。

请严格按 JSON 格式输出，不要输出其他内容：
{
  "has_risk": true/false,
  "risk_level": "高/中/低/无",
  "risk_points": [
    {
      "risk_description": "风险点描述",
      "risk_reason": "为什么这是风险",
      "risk_level": "高/中/低"
    }
  ],
  "overall_assessment": "对这个条款的整体评估"
}

风险等级判断标准：
- 高风险：可能导致合同无效、重大经济损失、严重违法
- 中风险：可能导致纠纷、权利义务不对等、条款不明确
- 低风险：表述不严谨、有小瑕疵但不影响实质
- 无风险：条款合法合规、权利义务对等

特别注意以下常见风险：
1. 格式条款中免除己方责任、加重对方责任的条款
2. 违约金过高或过低
3. 争议解决条款不明确或对己方不利
4. 免责条款违反法律强制性规定
5. 履行期限、方式不明确
6. 质量标准不明确
7. 解除合同条件不公平
"""


class RiskAgent(BaseAgent):
    """风险识别 Agent：识别条款风险"""
    
    def __init__(self):
        super().__init__(
            name="风险识别Agent",
            system_prompt=RISK_SYSTEM_PROMPT,
            temperature=0.3
        )
    
    def analyze(self, clause_title: str, clause_content: str, contract_type: str = "未知") -> dict:
        """分析单个条款的风险"""
        user_input = f"""合同类型：{contract_type}

请审查以下合同条款，识别风险：

【条款标题】{clause_title}

【条款内容】{clause_content}

请输出 JSON 格式的风险分析结果。"""
        
        return self.run_json(user_input)
