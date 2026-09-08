from app.core.agent_base import BaseAgent


COMPLIANCE_SYSTEM_PROMPT = """你是一个合规律师，专门负责检查合同条款是否符合法律法规。

你的任务是根据提供的法律参考资料，判断合同条款是否合规，并指出具体的法律依据。

请严格按 JSON 格式输出，不要输出其他内容：
{
  "is_compliant": true/false,
  "legal_basis": ["相关法律条文1", "相关法律条文2"],
  "violation_points": [
    {
      "violation_description": "违规点描述",
      "related_law": "违反的具体法律条文",
      "consequence": "可能导致的法律后果"
    }
  ],
  "compliance_note": "合规说明"
}

判断原则：
1. 违反法律、行政法规强制性规定的条款无效
2. 格式条款免除己方责任、加重对方责任、排除对方主要权利的无效
3. 造成对方人身损害的免责条款无效
4. 因故意或重大过失造成对方财产损失的免责条款无效
5. 违约金过分高于损失的，当事人可以请求减少
"""


class ComplianceAgent(BaseAgent):
    """合规比对 Agent：检查条款是否符合法律法规"""
    
    def __init__(self):
        super().__init__(
            name="合规比对Agent",
            system_prompt=COMPLIANCE_SYSTEM_PROMPT,
            temperature=0.2
        )
    
    def analyze(self, clause_title: str, clause_content: str, legal_references: str) -> dict:
        """分析条款合规性"""
        user_input = f"""【法律参考资料】
{legal_references}

【待审查条款】
标题：{clause_title}
内容：{clause_content}

请根据以上法律参考资料，判断该条款是否合规，并输出 JSON 格式结果。"""
        
        return self.run_json(user_input)
