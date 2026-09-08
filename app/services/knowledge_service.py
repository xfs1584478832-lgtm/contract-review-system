import os
import json
from typing import List, Optional
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.config import settings
from app.utils.logger import logger


class KnowledgeService:
    """法律知识库服务"""
    
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        )
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(settings.CHROMA_PATH, exist_ok=True)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    def _get_vector_db(self, collection_name: str = "law_knowledge") -> Chroma:
        """获取或创建向量数据库"""
        return Chroma(
            persist_directory=settings.CHROMA_PATH,
            embedding_function=self.embeddings,
            collection_name=collection_name
        )
    
    def load_document(self, file_path: str) -> List[Document]:
        """加载文档，支持 TXT/PDF/DOCX"""
        logger.info(f"加载文档: {file_path}")
        
        if file_path.endswith('.txt'):
            loader = TextLoader(file_path, encoding='utf-8')
        elif file_path.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {file_path}")
        
        documents = loader.load()
        logger.info(f"文档加载完成，共 {len(documents)} 页/段")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """文档切块"""
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"文档切块完成，共 {len(chunks)} 块")
        return chunks
    
    def add_documents(self, file_path: str, collection_name: str = "law_knowledge") -> dict:
        """加载文档并加入知识库"""
        try:
            documents = self.load_document(file_path)
            chunks = self.split_documents(documents)
            
            filename = os.path.basename(file_path)
            for chunk in chunks:
                chunk.metadata["source"] = filename
                chunk.metadata["file_type"] = os.path.splitext(filename)[1]
            
            db = self._get_vector_db(collection_name)
            db.add_documents(chunks)
            
            logger.info(f"文档 {filename} 已加入知识库，共 {len(chunks)} 块")
            
            return {
                "filename": filename,
                "chunks_count": len(chunks),
                "collection": collection_name
            }
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}", exc_info=True)
            raise
    
    def search(self, query: str, top_k: int = 3, collection_name: str = "law_knowledge") -> List[dict]:
        """检索相关文档"""
        db = self._get_vector_db(collection_name)
        results = db.similarity_search(query, k=top_k)
        
        return [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page", 0)
            }
            for doc in results
        ]
    
    def get_stats(self, collection_name: str = "law_knowledge") -> dict:
        """获取知识库统计信息"""
        db = self._get_vector_db(collection_name)
        collection = db._collection
        count = collection.count()
        return {
            "collection": collection_name,
            "documents_count": count
        }
    
    def clear_collection(self, collection_name: str = "law_knowledge"):
        """清空知识库"""
        db = self._get_vector_db(collection_name)
        db.delete_collection()
        logger.info(f"知识库 {collection_name} 已清空")
    
    def _get_imported_files(self) -> set:
        """获取已导入的文件列表"""
        record_file = os.path.join(settings.CHROMA_PATH, "imported_files.json")
        if os.path.exists(record_file):
            with open(record_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    
    def _save_imported_files(self, files: set):
        """保存已导入的文件列表"""
        record_file = os.path.join(settings.CHROMA_PATH, "imported_files.json")
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(list(files), f, ensure_ascii=False, indent=2)
    
    def auto_import(self, folder_path: str = None) -> dict:
        """自动遍历文件夹，导入所有新文档（只导入没导入过的）"""
        if folder_path is None:
            folder_path = os.path.join("data", "knowledge_base")
        
        os.makedirs(folder_path, exist_ok=True)
        
        supported = ['.txt', '.pdf', '.docx']
        imported = self._get_imported_files()
        
        new_files = []
        for filename in os.listdir(folder_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in supported and filename not in imported:
                new_files.append(filename)
        
        if not new_files:
            stats = self.get_stats()
            logger.info(f"自动扫描完成，没有新文档（知识库已有 {len(imported)} 个文件）")
            return {
                "scanned_folder": folder_path,
                "new_imported": 0,
                "failed": 0,
                "total_imported": len(imported),
                "skipped": len(imported),
                "knowledge_base_chunks": stats['documents_count']
            }
        
        logger.info(f"自动扫描发现 {len(new_files)} 个新文档，开始导入...")
        
        success = 0
        failed = 0
        newly_imported = []
        
        for filename in new_files:
            file_path = os.path.join(folder_path, filename)
            try:
                result = self.add_documents(file_path)
                imported.add(filename)
                newly_imported.append(filename)
                success += 1
                logger.info(f"  ✓ 导入成功: {filename}（{result['chunks_count']} 块）")
            except Exception as e:
                failed += 1
                logger.error(f"  ✗ 导入失败: {filename} - {str(e)}")
        
        self._save_imported_files(imported)
        stats = self.get_stats()
        
        result = {
            "scanned_folder": folder_path,
            "new_imported": success,
            "failed": failed,
            "total_imported": len(imported),
            "new_files": newly_imported,
            "knowledge_base_chunks": stats['documents_count']
        }
        
        logger.info(f"自动导入完成：成功 {success} 个，失败 {failed} 个，知识库共 {stats['documents_count']} 块")
        return result


# 全局单例
knowledge_service = KnowledgeService()
