import json
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.contract import Contract
from app.agents import ClauseAgent, RiskAgent, ComplianceAgent, SuggestionAgent
from app.services.knowledge_service import knowledge_service
from app.utils.logger import logger


class ReviewService:
    """合同审查服务：调度多个 Agent 协作完成审查"""
    
    def __init__(self):
        self.clause_agent = ClauseAgent()
        self.risk_agent = RiskAgent()
        self.compliance_agent = ComplianceAgent()
        self.suggestion_agent = SuggestionAgent()
    
    def review_contract(self, contract_id: int, db: Session) -> Dict:
        """完整审查合同"""
        logger.info(f"开始审查合同 ID={contract_id}")

        # 1. 获取合同
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise ValueError("合同不存在")

        if not contract.clauses:
            raise ValueError("合同尚未解析，请先解析合同")

        clauses = contract.clauses
        logger.info(f"合同共 {len(clauses)} 个条款，开始逐条审查")
        
        # 2. 逐条审查
        review_results = []
        high_risks = 0
        medium_risks = 0
        low_risks = 0
        
        for i, clause in enumerate(clauses):
            logger.info(f"审查第 {i+1}/{len(clauses)} 条: {clause.get('title', '')[:30]}")
            
            try:
                clause_result = self._review_single_clause(
                    clause=clause,
                    contract_type=contract.contract_type
                )
                review_results.append(clause_result)
                
                # 统计风险
                risk_level = clause_result.get("risk_analysis", {}).get("risk_level", "无")
                if risk_level == "高":
                    high_risks += 1
                elif risk_level == "中":
                    medium_risks += 1
                elif risk_level == "低":
                    low_risks += 1
                    
            except Exception as e:
                logger.error(f"第 {i+1} 条审查失败: {str(e)}")
                review_results.append({
                    "clause_index": i + 1,
                    "clause_title": clause.get("title", ""),
                    "error": str(e),
                    "risk_analysis": {"risk_level": "未知", "has_risk": False}
                })
        
        # 3. 生成审查报告
        report = self._generate_report(
            contract=contract,
            review_results=review_results,
            high_risks=high_risks,
            medium_risks=medium_risks,
            low_risks=low_risks
        )
        
        # 4. 保存审查结果到数据库（含审查时间，随报告一起持久化）
        report["review_time"] = datetime.now().isoformat()
        contract.review_result = report
        contract.status = "reviewed"
        db.commit()

        logger.info(f"合同审查完成：高风险 {high_risks}，中风险 {medium_risks}，低风险 {low_risks}")

        return report

    def review_contract_background(self, contract_id: int):
        """后台审查任务：使用独立数据库会话，供 FastAPI BackgroundTasks 调用

        审查耗时较长（多条款 × 多 Agent 调用 LLM），放在后台线程执行，
        接口立即返回；前端通过 GET /review/{id} 轮询审查状态。
        """
        db = SessionLocal()
        try:
            self.review_contract(contract_id, db)
        except Exception as e:
            logger.error(f"后台审查失败，合同 ID={contract_id}: {str(e)}", exc_info=True)
            # 记录失败状态，便于前端查询时感知
            try:
                contract = db.query(Contract).filter(Contract.id == contract_id).first()
                if contract:
                    contract.status = "review_failed"
                    contract.review_result = {"status": "failed", "error": str(e)}
                    db.commit()
            except Exception:
                logger.error("记录审查失败状态时出错", exc_info=True)
        finally:
            db.close()
    
    def _review_single_clause(self, clause: Dict, contract_type: str) -> Dict:
        """审查单个条款：4个Agent流水线处理"""
        clause_title = clause.get("title", "")
        clause_content = clause.get("content", "")
        clause_index = clause.get("index", 0)
        
        # Agent 1: 条款抽取分析
        clause_analysis = self.clause_agent.analyze(clause_title, clause_content)
        
        # Agent 2: 风险识别
        risk_analysis = self.risk_agent.analyze(clause_title, clause_content, contract_type)
        
        # Agent 3: 合规比对（每条都先检索法律知识库，为合规判断提供法条依据）
        has_risk = risk_analysis.get("has_risk", False)
        search_query = f"{clause_title} {clause_content[:100]}"
        legal_docs = knowledge_service.search(search_query, top_k=2)
        legal_references = "\n\n".join([doc["content"] for doc in legal_docs])

        compliance_analysis = self.compliance_agent.analyze(
            clause_title, clause_content, legal_references
        )
        
        # Agent 4: 修改建议（只有有风险或不合规才生成）
        suggestion_analysis = {}
        if has_risk or not compliance_analysis.get("is_compliant", True):
            suggestion_analysis = self.suggestion_agent.analyze(
                clause_title, clause_content, risk_analysis, compliance_analysis
            )
        
        return {
            "clause_index": clause_index,
            "clause_title": clause_title,
            "clause_type": clause_analysis.get("clause_type", "其他"),
            "key_points": clause_analysis.get("key_points", []),
            "risk_analysis": risk_analysis,
            "compliance_analysis": compliance_analysis,
            "suggestion_analysis": suggestion_analysis,
            "legal_references": legal_references
        }
    
    def _generate_report(
        self,
        contract: Contract,
        review_results: List[Dict],
        high_risks: int,
        medium_risks: int,
        low_risks: int
    ) -> Dict:
        """生成审查报告"""
        total_clauses = len(review_results)
        risky_clauses = high_risks + medium_risks
        
        # 风险等级评定
        if high_risks > 0:
            overall_level = "高风险"
            overall_suggestion = "合同存在重大法律风险，建议修改后再签署"
        elif medium_risks > 2:
            overall_level = "中风险"
            overall_suggestion = "合同存在一定法律风险，建议酌情修改"
        elif medium_risks > 0 or low_risks > 3:
            overall_level = "低风险"
            overall_suggestion = "合同基本合规，建议关注小瑕疵"
        else:
            overall_level = "低风险"
            overall_suggestion = "合同合规情况良好，可以签署"
        
        # 提取高风险条款清单
        high_risk_list = [
            {
                "clause_index": r["clause_index"],
                "clause_title": r["clause_title"],
                "risk_points": r.get("risk_analysis", {}).get("risk_points", []),
                "suggestions": r.get("suggestion_analysis", {}).get("suggestions", [])
            }
            for r in review_results
            if r.get("risk_analysis", {}).get("risk_level") == "高"
        ]
        
        return {
            "summary": {
                "contract_name": contract.filename,
                "contract_type": contract.contract_type,
                "total_clauses": total_clauses,
                "reviewed_clauses": total_clauses,
                "high_risks": high_risks,
                "medium_risks": medium_risks,
                "low_risks": low_risks,
                "overall_risk_level": overall_level,
                "overall_suggestion": overall_suggestion
            },
            "high_risk_clauses": high_risk_list,
            "detailed_review": review_results,
        }


# 全局单例
review_service = ReviewService()
