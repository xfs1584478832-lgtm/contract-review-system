# 法眼 - 智能合同审查助手

基于 RAG + 多 Agent + LoRA 微调的企业级智能合同审查系统。

## 功能特性

- 📄 多格式合同解析（PDF/Word）
- 🔍 法律知识库检索（RAG）
- 🤖 多 Agent 协作审查（风险识别/修改建议/合规比对）
- 🎯 法律专用模型微调（LoRA）
- 🔒 权限管理与审计留痕
- 👥 团队协作与知识沉淀
- 💰 精细化成本控制

## 技术栈

- 后端：FastAPI + SQLAlchemy
- 大模型：DeepSeek-V3 + LoRA 微调模型
- 向量数据库：ChromaDB
- Embedding：text2vec-base-chinese
- 前端：HTML + CSS + JavaScript
- 部署：Docker

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 启动服务
uvicorn app.main:app --reload
