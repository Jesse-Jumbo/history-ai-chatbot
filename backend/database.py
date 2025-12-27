from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, List, Dict
import json

# SQLite 資料庫路徑
DATABASE_URL = "sqlite:///./history_qa.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class QAPair(Base):
    __tablename__ = "qa_pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, index=True)
    answer = Column(Text)
    category = Column(String, default="general")  # 歷史類別

class Document(Base):
    """歷史資料文檔表"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)  # 文檔標題
    content = Column(Text)  # 文檔內容
    category = Column(String, default="general")  # 分類（如：台灣史、中國史等）
    source = Column(String, index=True)  # 來源 ID（CSV 中的 id 欄位）
    embedding = Column(Text, nullable=True)  # 向量嵌入（JSON 格式）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class BotConfig(Base):
    """機器人配置表（角色/身份設定）"""
    __tablename__ = "bot_config"
    
    id = Column(Integer, primary_key=True, index=True)
    role_name = Column(String, default="歷史系 AI 助手")  # 角色名稱（如：吳新榮、鄭成功）
    role_description = Column(Text, nullable=True)  # 角色描述（如：基於吳新榮日記的 QA 機器人）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化資料庫，建立表格並遷移現有表結構"""
    Base.metadata.create_all(bind=engine)
    
    # 每次啟動時重置機器人配置為默認值
    db = SessionLocal()
    try:
        config = db.query(BotConfig).first()
        default_role_name = "成功大學歷史系的對話機器人"
        default_role_description = "我是成功大學歷史系的對話機器人，專門回答歷史相關問題。我可以結合我的知識和您提供的歷史資料來回答問題。"
        
        if not config:
            # 如果不存在，創建默認配置
            config = BotConfig(
                role_name=default_role_name,
                role_description=default_role_description
            )
            db.add(config)
        else:
            # 如果存在，重置為默認值（每次啟動時重置）
            config.role_name = default_role_name
            config.role_description = default_role_description
            config.updated_at = datetime.now()
        
        db.commit()
    finally:
        db.close()
    
    # 不再需要 embedding 列，已移除向量搜索功能
    
    # 不再插入範例資料，讓使用者自行上傳

def get_answer_from_db(question: str) -> Optional[str]:
    """
    從資料庫搜尋答案（問答對）
    使用簡單的關鍵字匹配
    """
    db = SessionLocal()
    try:
        # 簡單的關鍵字搜尋（可以改進為全文搜尋）
        qa_pairs = db.query(QAPair).filter(
            QAPair.question.contains(question) | 
            QAPair.answer.contains(question)
        ).all()
        
        if qa_pairs:
            # 返回第一個匹配的答案
            return qa_pairs[0].answer
        return None
    finally:
        db.close()

def search_documents(question: str, limit: int = None, use_embedding: bool = True) -> List[Dict]:
    """
    從資料庫搜尋相關文檔段落（僅使用向量相似度搜索）
    
    Args:
        question: 查詢問題
        limit: 返回結果數量限制
        use_embedding: 是否使用向量搜索（預設 True，必須為 True）
    
    Returns:
        list of dict: [{"source": str, "content": str, "full_content": str, "similarity": float, "doc_titles": List[str]}, ...]
    """
    db = SessionLocal()
    try:
        # 只使用向量搜索
        if not question.strip():
            return []
        
        from embedding_service import get_embedding, search_by_similarity
        
        # 生成查詢的向量嵌入
        query_embedding = get_embedding(question)
        
        if not query_embedding:
            return []
        
        # 優化：只加載必要的字段，減少內存使用
        # 先獲取所有有 embedding 的文檔 ID 和 embedding（用於相似度計算）
        docs_with_embedding = db.query(
            Document.id,
            Document.embedding
        ).filter(
            Document.embedding.isnot(None)
        ).all()
        
        if not docs_with_embedding:
            return []
        
        # 準備文檔向量列表（只包含 ID 和 embedding，用於快速相似度計算）
        doc_embeddings = [
            (doc.id, doc.embedding)
            for doc in docs_with_embedding
        ]
        
        # 向量相似度搜索
        search_limit = limit if limit else 20
        # 優化：檢索更多文檔以提升準確度（檢索 5 倍數量，確保找到所有相關文檔）
        # 如果 limit 很大（如 100），則最多檢索 500 個文檔
        top_k = min(search_limit * 5, 500)  # 最多 500 個
        similar_docs = search_by_similarity(
            query_embedding,
            doc_embeddings,
            top_k=top_k,
            threshold=0.2  # 降低閾值以獲取更多相關結果
        )
        
        if not similar_docs:
            return []
        
        # 轉換為文檔對象（只加載需要的文檔）
        doc_ids = [item[1] for item in similar_docs]  # item[1] 是 doc_id
        documents = db.query(
            Document.id,
            Document.title,
            Document.content,
            Document.source
        ).filter(
            Document.id.in_(doc_ids)
        ).all()
        
        # 按相似度排序（優化：使用字典快速查找）
        similarity_map = {item[1]: item[0] for item in similar_docs}
        # 將 documents 轉換為列表以便排序
        documents = list(documents)
        documents.sort(key=lambda d: similarity_map.get(d.id, 0), reverse=True)
        
        # 去重並按來源分組
        seen_doc_ids = set()
        seen_sources = {}
        
        for doc in documents:
            if doc.id not in seen_doc_ids:
                source_id = doc.source or "unknown"
                if source_id not in seen_sources:
                    seen_sources[source_id] = []
                seen_sources[source_id].append((doc, similarity_map.get(doc.id, 0)))
                seen_doc_ids.add(doc.id)
        
        # 格式化結果
        max_sources = search_limit if search_limit else 10
        results = []
        for source_id, doc_list in list(seen_sources.items())[:max_sources]:
            # 按相似度排序該來源的文檔
            doc_list.sort(key=lambda x: x[1], reverse=True)
            docs = [d[0] for d in doc_list]
            
            # 合併同一來源的所有內容
            all_content = " ".join([doc.content for doc in docs])
            avg_similarity = sum(d[1] for d in doc_list) / len(doc_list)
            
            # 提取內容（優先使用完整內容，如果太長則截取）
            if len(all_content) <= 3000:
                content = all_content
            else:
                # 如果內容太長，取前3000字符
                content = all_content[:3000] + "..."
            
            doc_titles = [doc.title for doc in docs if doc.title]
            
            results.append({
                "source": source_id,
                "content": content,
                "full_content": all_content,
                "count": len(docs),
                "doc_titles": doc_titles,
                "similarity": avg_similarity
            })
        
        return results
    finally:
        db.close()

def add_document(title: str, content: str, category: str = "general", source: str = ""):
    """
    新增文檔到資料庫
    
    Args:
        title: 文檔標題
        content: 文檔內容
        category: 分類
        source: 來源 ID
    
    Returns:
        文檔 ID
    """
    db = SessionLocal()
    try:
        doc = Document(
            title=title or f"資料-{source}",
            content=content,
            category=category,
            source=source,
            embedding=None  # 不再生成 embedding
        )
        db.add(doc)
        db.commit()
        return doc.id
    finally:
        db.close()

def batch_add_documents_from_csv(rows: List[Dict[str, str]], generate_embeddings: bool = False) -> int:
    """
    批量從 CSV 資料新增文檔
    
    Args:
        rows: [{"id": "doc_title", "source": "source_id", "text": "content"}, ...]
        - id: 資料名稱（會作為 title）
        - source: 來源 ID（CSV 文件名）
        - text: 內容
        generate_embeddings: 不再使用，保留參數以保持兼容性
    
    Returns:
        新增的文檔數量
    """
    db = SessionLocal()
    try:
        count = 0
        
        # 準備文檔數據並直接添加到資料庫
        for row in rows:
            doc_title = row.get("id", "").strip()
            source_id = row.get("source", "").strip()
            text = row.get("text", "").strip()
            
            if doc_title and text and source_id:
                doc = Document(
                    title=doc_title,
                    content=text,
                    category="CSV導入",
                    source=source_id,
                    embedding=None  # 不再生成 embedding
                )
                db.add(doc)
                count += 1
        
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_all_documents():
    """獲取所有文檔列表"""
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        return [{
            "id": doc.id,
            "title": doc.title,
            "category": doc.category,
            "source": doc.source,
            "created_at": doc.created_at.isoformat() if doc.created_at else None
        } for doc in docs]
    finally:
        db.close()

def get_all_documents_with_content():
    """獲取所有文檔及其內容（用於 Gemini API）"""
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        # 按來源分組
        source_map = {}
        for doc in docs:
            source_id = doc.source or "unknown"
            if source_id not in source_map:
                source_map[source_id] = []
            source_map[source_id].append({
                "title": doc.title,
                "content": doc.content or ""
            })
        
        # 轉換為列表格式
        result = []
        for source_id, doc_list in source_map.items():
            # 合併同一來源的所有內容
            all_titles = [d["title"] for d in doc_list if d["title"]]
            all_content = "\n\n".join([
                f"{d['title']}\n{d['content']}" if d['title'] else d['content']
                for d in doc_list
                if d['content']
            ])
            
            result.append({
                "source": source_id,
                "title": ", ".join(all_titles[:5]) if all_titles else "無標題",
                "content": all_content,
                "doc_titles": all_titles
            })
        
        return result
    finally:
        db.close()


def get_elderly_documents_with_content():
    """只獲取老人訪談文檔（category=elderly_interview），按來源合併內容"""
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.category == "elderly_interview").all()
        if not docs:
            return []

        source_map: Dict[str, List[Dict[str, str]]] = {}
        for doc in docs:
            source_id = doc.source or "unknown"
            if source_id not in source_map:
                source_map[source_id] = []
            source_map[source_id].append(
                {
                    "title": doc.title,
                    "content": doc.content or "",
                }
            )

        result = []
        for source_id, doc_list in source_map.items():
            all_titles = [d["title"] for d in doc_list if d["title"]]
            all_content = "\n\n".join(
                f"{d['title']}\n{d['content']}" if d["title"] else d["content"]
                for d in doc_list
                if d["content"]
            )

            result.append(
                {
                    "source": source_id,
                    "title": ", ".join(all_titles[:5]) if all_titles else "無標題",
                    "content": all_content,
                    "doc_titles": all_titles,
                }
            )

        return result
    finally:
        db.close()

def get_document_by_id(doc_id: int) -> Optional[Dict]:
    """根據 ID 獲取單個文檔的詳細內容"""
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return None
        return {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "category": doc.category,
            "source": doc.source,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        }
    finally:
        db.close()

def add_qa_pair(question: str, answer: str, category: str = "general"):
    """新增問答對到資料庫"""
    db = SessionLocal()
    try:
        qa = QAPair(question=question, answer=answer, category=category)
        db.add(qa)
        db.commit()
    finally:
        db.close()

def get_bot_config() -> Dict:
    """獲取機器人配置（角色/身份）"""
    db = SessionLocal()
    try:
        config = db.query(BotConfig).first()
        if not config:
            return {
                "role_name": "成功大學歷史系的對話機器人",
                "role_description": "我是成功大學歷史系的對話機器人，專門回答歷史相關問題。我可以結合我的知識和您提供的歷史資料來回答問題。"
            }
        return {
            "role_name": config.role_name,
            "role_description": config.role_description or ""
        }
    finally:
        db.close()

def update_bot_config(role_name: str, role_description: str = None):
    """更新機器人配置（角色/身份）"""
    db = SessionLocal()
    try:
        config = db.query(BotConfig).first()
        if not config:
            config = BotConfig(role_name=role_name, role_description=role_description)
            db.add(config)
        else:
            config.role_name = role_name
            if role_description is not None:
                config.role_description = role_description
            config.updated_at = datetime.now()
        db.commit()
    finally:
        db.close()

