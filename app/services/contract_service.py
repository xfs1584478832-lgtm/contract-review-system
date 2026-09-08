import os
import re
import json
from typing import List, Dict, Optional
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from app.config import settings
from app.utils.logger import logger


class ContractService:
    """合同解析服务"""
    
    # 合同类型关键词映射
    CONTRACT_TYPE_KEYWORDS = {
        "买卖合同": ["买卖", "购销", "采购", "供货", "销售"],
        "租赁合同": ["租赁", "出租", "承租"],
        "劳动合同": ["劳动", "聘用", "雇佣", "劳务"],
        "借款合同": ["借款", "贷款", "借贷"],
        "承揽合同": ["承揽", "加工", "定做"],
        "建设工程合同": ["建设工程", "施工", "工程承包"],
        "技术合同": ["技术开发", "技术转让", "技术服务", "技术咨询"],
        "保管合同": ["保管", "仓储"],
        "委托合同": ["委托", "代理"],
        "运输合同": ["运输", "货运", "客运"],
    }
    
    # 条款类型关键词
    CLAUSE_TYPE_KEYWORDS = {
        "标的": ["标的", "产品", "货物", "服务内容", "工作内容"],
        "数量质量": ["数量", "质量", "规格", "型号", "标准"],
        "价款支付": ["价款", "报酬", "金额", "价格", "支付", "付款", "结算"],
        "履行交付": ["履行", "交付", "交货", "期限", "时间", "地点", "方式"],
        "验收": ["验收", "检验", "检查"],
        "违约责任": ["违约", "赔偿", "违约金", "滞纳金"],
        "争议解决": ["争议", "纠纷", "诉讼", "仲裁", "管辖"],
        "不可抗力": ["不可抗力", "免责"],
        "合同变更": ["变更", "解除", "终止", "撤销"],
        "其他": ["其他", "附则", "生效", "份数"],
    }
    
    def load_contract(self, file_path: str) -> str:
        """加载合同全文"""
        logger.info(f"加载合同: {file_path}")
        
        if file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        elif file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path}")
        
        documents = loader.load()
        full_text = "\n".join([doc.page_content for doc in documents])
        
        # 清理多余空白
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = full_text.strip()
        
        logger.info(f"合同加载完成，共 {len(full_text)} 字")
        return full_text
    
    def detect_contract_type(self, text: str) -> str:
        """识别合同类型"""
        # 取前500字判断（合同类型一般在标题或开头）
        header = text[:500]
        
        scores = {}
        for contract_type, keywords in self.CONTRACT_TYPE_KEYWORDS.items():
            score = sum(header.count(kw) for kw in keywords)
            if score > 0:
                scores[contract_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "其他合同"
    
    def extract_party(self, text: str, party_keywords: List[str]) -> Optional[str]:
        """抽取合同当事人"""
        # 取前1000字（当事人信息一般在开头）
        header = text[:1000]
        
        for keyword in party_keywords:
            # 匹配 "甲方：xxx" 或 "甲方（xxx）：xxx" 等格式
            patterns = [
                rf'{keyword}[：:]\s*(.+?)(?:\n|$)',
                rf'{keyword}[（(][^）)]*[）)]\s*[：:]\s*(.+?)(?:\n|$)',
                rf'{keyword}\s*(.+?)(?:\n|$)',
            ]
            for pattern in patterns:
                match = re.search(pattern, header)
                if match:
                    party = match.group(1).strip()
                    # 过滤掉太短或明显不是公司名的
                    if len(party) > 2 and not any(c in party for c in '：:；;。，,'):
                        return party[:200]
        return None
    
    def extract_amount(self, text: str) -> tuple:
        """抽取合同金额，返回(大写金额, 数字金额)"""
        # 匹配 "人民币xxx元" 或 "金额：xxx"
        amount_patterns = [
            r'人民币\s*([0-9零一二三四五六七八九十百千万亿贰叁肆伍陆柒捌玖拾佰仟]+)\s*元',
            r'合同(?:总)?金额[：:]\s*人民币?\s*([0-9零一二三四五六七八九十百千万亿贰叁肆伍陆柒捌玖拾佰仟万]+)\s*元',
            r'价款[：:]\s*([0-9零一二三四五六七八九十百千万亿贰叁肆伍陆柒捌玖拾佰仟万]+)\s*元',
            r'([0-9,]+\.?[0-9]*)\s*元',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1).strip()
                # 尝试转数字
                amount_num = self._convert_amount_to_number(amount_str)
                return amount_str, amount_num
        
        return None, None
    
    def _convert_amount_to_number(self, amount_str: str) -> Optional[float]:
        """把金额字符串转成数字（简单处理）"""
        # 已经是数字的情况
        try:
            return float(amount_str.replace(',', ''))
        except ValueError:
            pass
        
        # 中文数字转数字（简化版，只处理常见情况）
        chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
            '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10,
        }
        # 简化处理，实际项目可以用更完善的库
        try:
            # 提取万、亿等单位
            if '亿' in amount_str:
                parts = amount_str.split('亿')
                return float(parts[0]) * 100000000
            elif '万' in amount_str:
                parts = amount_str.split('万')
                return float(parts[0]) * 10000
        except (ValueError, IndexError):
            pass
        
        return None
    
    def extract_dates(self, text: str) -> dict:
        """抽取日期信息"""
        result = {
            "signing_date": None,
            "start_date": None,
            "end_date": None,
        }
        
        # 签订日期
        sign_patterns = [
            r'签订日期[：:]\s*(\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}[日]?)',
            r'签约日期[：:]\s*(\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}[日]?)',
            r'订立日期[：:]\s*(\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}[日]?)',
        ]
        for pattern in sign_patterns:
            match = re.search(pattern, text)
            if match:
                result["signing_date"] = match.group(1).strip()
                break
        
        # 履行期限
        duration_patterns = [
            r'自\s*(\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}[日]?)\s*起?\s*至\s*(\d{4}[-年/.]\d{1,2}[-月/.]\d{1,2}[日]?)',
            r'有效期\s*[：:]\s*自\s*(.+?)\s*至\s*(.+?)(?:\n|。)',
            r'租赁期限\s*[：:]\s*自\s*(.+?)\s*至\s*(.+?)(?:\n|。)',
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, text)
            if match:
                result["start_date"] = match.group(1).strip()
                result["end_date"] = match.group(2).strip()
                break
        
        return result
    
    def split_clauses(self, text: str) -> List[Dict]:
        """自动分割合同条款"""
        clauses = []
        
        # 匹配 "第一条" "第二条" 或 "1." "2." 等格式
        clause_pattern = re.compile(
            r'(第[一二三四五六七八九十百千0-9]+条|[0-9]+[.、])\s*(.+?)(?=(?:第[一二三四五六七八九十百千0-9]+条|[0-9]+[.、])|\Z)',
            re.DOTALL
        )
        
        matches = clause_pattern.findall(text)
        
        if matches:
            for i, (clause_num, clause_content) in enumerate(matches):
                clause_content = clause_content.strip()
                if not clause_content:
                    continue
                
                # 提取条款标题（第一行）
                lines = clause_content.split('\n', 1)
                title = lines[0].strip()[:100]
                content = clause_content
                
                # 识别条款类型
                clause_type = self._detect_clause_type(title + content)
                
                clauses.append({
                    "index": i + 1,
                    "number": clause_num,
                    "title": title,
                    "content": content,
                    "clause_type": clause_type,
                })
        else:
            # 如果没有标准条款格式，按段落分割
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            for i, para in enumerate(paragraphs):
                clause_type = self._detect_clause_type(para)
                clauses.append({
                    "index": i + 1,
                    "number": f"第{i+1}段",
                    "title": para[:50] + "..." if len(para) > 50 else para,
                    "content": para,
                    "clause_type": clause_type,
                })
        
        logger.info(f"合同分割完成，共 {len(clauses)} 个条款")
        return clauses
    
    def _detect_clause_type(self, text: str) -> str:
        """识别条款类型"""
        for clause_type, keywords in self.CLAUSE_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    return clause_type
        return "其他"
    
    def generate_summary(self, text: str, contract_type: str, clauses: List[Dict]) -> str:
        """生成合同摘要"""
        clause_types = set(c["clause_type"] for c in clauses)
        
        summary_parts = [f"本合同为{contract_type}，共{len(clauses)}个条款。"]
        summary_parts.append(f"包含以下主要内容：{'、'.join(clause_types)}。")
        
        return "".join(summary_parts)
    
    def parse_contract(self, file_path: str) -> Dict:
        """完整解析合同"""
        try:
            # 1. 加载全文
            full_text = self.load_contract(file_path)
            
            # 2. 识别类型
            contract_type = self.detect_contract_type(full_text)
            logger.info(f"合同类型: {contract_type}")
            
            # 3. 抽取当事人
            party_a = self.extract_party(full_text, ["甲方", "卖方", "出租方", "借款人", "委托方", "发包方"])
            party_b = self.extract_party(full_text, ["乙方", "买方", "承租方", "贷款人", "受托方", "承包方"])
            logger.info(f"甲方: {party_a}, 乙方: {party_b}")
            
            # 4. 抽取金额
            amount_str, amount_num = self.extract_amount(full_text)
            logger.info(f"合同金额: {amount_str} ({amount_num})")
            
            # 5. 抽取日期
            dates = self.extract_dates(full_text)
            logger.info(f"日期: {dates}")
            
            # 6. 分割条款
            clauses = self.split_clauses(full_text)
            
            # 7. 生成摘要
            summary = self.generate_summary(full_text, contract_type, clauses)
            
            return {
                "contract_type": contract_type,
                "party_a": party_a,
                "party_b": party_b,
                "contract_amount": amount_str,
                "contract_amount_num": amount_num,
                "start_date": dates["start_date"],
                "end_date": dates["end_date"],
                "signing_date": dates["signing_date"],
                "full_text": full_text,
                "clauses": clauses,
                "summary": summary,
                "status": "parsed",
            }
        except Exception as e:
            logger.error(f"合同解析失败: {str(e)}", exc_info=True)
            raise


# 全局单例
contract_service = ContractService()
