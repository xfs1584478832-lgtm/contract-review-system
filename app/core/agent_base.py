import json
from typing import Dict, Any, Optional
from openai import OpenAI
from app.config import settings
from app.utils.logger import logger


class BaseAgent:
    """Agent 基类，所有 Agent 都继承这个类"""
    
    def __init__(self, name: str, system_prompt: str, temperature: float = 0.3):
        self.name = name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.client = OpenAI(
            api_key=settings.SILICONFLOW_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=90.0  # 单次请求超时90秒，避免网络挂起时长时间阻塞审查流水线
        )
    
    def run(self, user_input: str, max_tokens: int = 2000) -> str:
        """运行 Agent，返回纯文本结果"""
        logger.info(f"[{self.name}] 开始处理...")
        
        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            result = response.choices[0].message.content
            logger.info(f"[{self.name}] 处理完成")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] 处理失败: {str(e)}", exc_info=True)
            raise
    
    def run_json(self, user_input: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """运行 Agent，返回 JSON 格式结果（自动解析）"""
        result = self.run(user_input, max_tokens)
        
        # 尝试解析 JSON
        try:
            # 清理可能的 markdown 代码块标记
            cleaned = result.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] JSON 解析失败: {str(e)}")
            logger.error(f"原始输出: {result[:500]}")
            # 解析失败时返回原始文本
            return {"raw_output": result, "parse_error": str(e)}
    
    def __repr__(self):
        return f"<Agent: {self.name}>"
