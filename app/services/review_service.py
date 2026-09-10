import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        self.max_workers = 3  # 并发数，保守设为3，避免API限流
    
    def review_contract(self, contract_id: int, db: Session) -> Dict:
        """完整审查合同（并发版）"""
        logger.info(f"开始审查合同 ID={contract_id}")

        # 1. 获取合同
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if not contract:
            raise ValueError("合同不存在")

        if not contract.clauses:
            raise ValueError("合同尚未解析，请先解析合同")

        # 标记审查中
        contract.status = "reviewing"
        db.commit()

        clauses = contract.clauses
        logger.info(f"合同共 {len(clauses)} 个条款，开始并发审查（{self.max_workers}线程）")

        # 2. 并发审查所有条款
        review_results = [None] * len(clauses)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务，记录索引
            future_to_index = {
                executor.submit(
                    self._review_single_clause, 
                    clause, 
                    contract.contract_type
                ): i
                for i, clause in enumerate(clauses)
            }
            
            # 按完成顺序收集结果
            completed = 0
            for future in as_completed(future_to_index):
                i = future_to_index[future]
                completed += 1
                try:
                    review_results[i] = future.result()
                    logger.info(f"审查进度: {completed}/{len(clauses)}")
                except Exception as e:
                    logger.error(f"第 {i+1} 条审查失败: {str(e)}")
                    review_results[i] = {
                        "clause_index": i + 1,
                        "clause_title": clauses[i].get("title", ""),
                        "error": str(e),
                        "risk_analysis": {"risk_level": "未知", "has_risk": False}
                    }

        # 3. 统计风险
        high_risks = medium_risks = low_risks = 0
        for r in review_results:
            risk_level = r.get("risk_analysis", {}).get("risk_level", "无")
            if risk_level == "高":
                high_risks += 1
            elif risk_level == "中":
                medium_risks += 1
            elif risk_level == "低":
                low_risks += 1

        # 4. 生成审查报告
        report = self._generate_report(
            contract=contract,
            review_results=review_results,
            high_risks=high_risks,
            medium_risks=medium_risks,
            low_risks=low_risks
        )
        
        # 5. 保存审查结果到数据库（含审查时间）
        report["review_time"] = datetime.now().isoformat()
        contract.review_result = report
        contract.status = "reviewed"
        db.commit()

        logger.info(f"合同审查完成：高风险 {high_risks}，中风险 {medium_risks}，低风险 {low_risks}")
        return report

    def review_contract_background(self, contract_id: int):
        """后台审查任务：使用独立数据库会话"""
        db = SessionLocal()
        try:
            self.review_contract(contract_id, db)
        except Exception as e:
            logger.error(f"后台审查失败，合同 ID={contract_id}: {str(e)}", exc_info=True)
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
        """审查单个条款：三阶段流水线（阶段1内部并发）

        阶段1（并发，三者互不依赖）：条款抽取Agent / 风险识别Agent / 知识库检索
        阶段2（依赖检索结果）：合规比对Agent
        阶段3（依赖风险+合规结果）：修改建议Agent（仅有风险或不合规时）
        """
        t_start = time.time()
        clause_title = clause.get("title", "")
        clause_content = clause.get("content", "")
        clause_index = clause.get("index", 0)

        # 阶段1：条款抽取、风险识别、知识库检索 并发执行
        search_query = f"{clause_title} {clause_content[:100]}"
        with ThreadPoolExecutor(max_workers=3) as inner:
            f_clause = inner.submit(
                self.clause_agent.analyze, clause_title, clause_content
            )
            f_risk = inner.submit(
                self.risk_agent.analyze, clause_title, clause_content, contract_type
            )
            f_search = inner.submit(knowledge_service.search, search_query, 2)

            clause_analysis = f_clause.result()
            risk_analysis = f_risk.result()
            legal_docs = f_search.result()

        has_risk = risk_analysis.get("has_risk", False)
        risk_level = risk_analysis.get("risk_level", "无")

        legal_references = "\n\n".join([doc["content"] for doc in legal_docs])

        # 阶段2：合规比对
        compliance_analysis = self.compliance_agent.analyze(
            clause_title, clause_content, legal_references
        )

        # 阶段3：修改建议（只有有风险或不合规才生成）
        suggestion_analysis = {}
        if has_risk or not compliance_analysis.get("is_compliant", True):
            suggestion_analysis = self.suggestion_agent.analyze(
                clause_title, clause_content, risk_analysis, compliance_analysis
            )

        logger.info(
            f"第 {clause_index} 条「{clause_title}」审查完成，"
            f"耗时 {time.time() - t_start:.1f}s，风险等级：{risk_level}"
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
