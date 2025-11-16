from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Optional, List, Dict
import os
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化資料庫，建立表格並遷移現有表結構"""
    Base.metadata.create_all(bind=engine)
    
    # 遷移現有表結構（添加缺失的列）
    db = SessionLocal()
    try:
        # 檢查 documents 表是否有 embedding 列
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('documents')]
        
        if 'embedding' not in columns:
            # 添加 embedding 列
            db.execute(text('ALTER TABLE documents ADD COLUMN embedding TEXT'))
            db.commit()
    except Exception as e:
        # 如果表不存在或其他錯誤，忽略（會在 create_all 中創建）
        pass
    finally:
        db.close()
    
    # 插入一些範例資料
    db = SessionLocal()
    try:
        # 檢查是否已有資料
        if db.query(QAPair).count() == 0:
            sample_qa = [
                QAPair(
                    question="什麼是台灣史？",
                    answer="台灣史是研究台灣這塊土地及其人民歷史發展的學科，涵蓋原住民文化、荷西時期、明鄭時期、清領時期、日治時期以及戰後至今的歷史變遷。",
                    category="台灣史"
                ),
                QAPair(
                    question="鄭成功何時來台？",
                    answer="鄭成功於1661年率軍來台，1662年擊敗荷蘭人，建立明鄭政權。",
                    category="台灣史"
                ),
                QAPair(
                    question="日治時期從哪一年開始？",
                    answer="日治時期從1895年開始，至1945年結束，共50年。",
                    category="台灣史"
                ),
            ]
            db.add_all(sample_qa)
            db.commit()
        
        # 插入範例文檔
        if db.query(Document).count() == 0:
            sample_docs = [
                Document(
                    title="台灣史概述",
                    content="台灣歷史可以追溯到數千年前的原住民文化。17世紀初，荷蘭人和西班牙人先後在台灣建立據點。1661年，鄭成功率軍來台，擊敗荷蘭人，建立明鄭政權。1683年，清朝統一台灣。1895年，台灣割讓給日本，開始了50年的日治時期。1945年，台灣光復，回歸中華民國。",
                    category="台灣史",
                    source="歷史教科書"
                ),
                Document(
                    title="鄭成功收復台灣",
                    content="鄭成功（1624-1662），原名鄭森，是明末清初的重要軍事將領。1661年4月，鄭成功率領25000名士兵和數百艘戰艦，從廈門出發，進攻台灣的荷蘭人。經過9個月的圍攻，1662年2月1日，荷蘭總督揆一投降，台灣正式回歸中國。鄭成功在台灣建立政權，實施屯田政策，發展農業，為台灣的開發奠定了基礎。",
                    category="台灣史",
                    source="歷史文獻"
                ),
            ]
            db.add_all(sample_docs)
            db.commit()
    finally:
        db.close()

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

def add_document(title: str, content: str, category: str = "general", source: str = "", generate_embedding: bool = True):
    """
    新增文檔到資料庫，並可選生成向量嵌入
    
    Args:
        title: 文檔標題
        content: 文檔內容
        category: 分類
        source: 來源 ID
        generate_embedding: 是否生成向量嵌入（預設 True）
    
    Returns:
        文檔 ID
    """
    db = SessionLocal()
    try:
        embedding = None
        if generate_embedding and content:
            try:
                from embedding_service import get_embedding
                # 生成 embedding（使用標題+內容，限制長度以避免過長）
                text_for_embedding = f"{title} {content}"[:2000]  # 限制長度
                embedding_list = get_embedding(text_for_embedding)
                if embedding_list:
                    embedding = json.dumps(embedding_list)
            except Exception as e:
                pass
        
        doc = Document(
            title=title or f"資料-{source}",
            content=content,
            category=category,
            source=source,
            embedding=embedding
        )
        db.add(doc)
        db.commit()
        return doc.id
    finally:
        db.close()

def batch_add_documents_from_csv(rows: List[Dict[str, str]], generate_embeddings: bool = True) -> int:
    """
    批量從 CSV 資料新增文檔，並可選批量生成向量嵌入
    
    Args:
        rows: [{"id": "doc_title", "source": "source_id", "text": "content"}, ...]
        - id: 資料名稱（會作為 title）
        - source: 來源 ID（CSV 文件名）
        - text: 內容
        generate_embeddings: 是否生成向量嵌入（預設 True，但批量生成可能較慢）
    
    Returns:
        新增的文檔數量
    """
    db = SessionLocal()
    try:
        from embedding_service import batch_get_embeddings
        
        count = 0
        docs_to_add = []
        
        # 準備文檔數據
        for row in rows:
            doc_title = row.get("id", "").strip()
            source_id = row.get("source", "").strip()
            text = row.get("text", "").strip()
            
            if doc_title and text and source_id:
                docs_to_add.append({
                    "title": doc_title,
                    "content": text,
                    "source": source_id
                })
        
        # 批量生成 embeddings（如果啟用）
        embeddings = None
        if generate_embeddings and docs_to_add:
            try:
                # 先測試 embedding 服務是否可用
                from embedding_service import get_embedding, batch_get_embeddings
                test_embedding = get_embedding("測試")
                if test_embedding is None:
                    generate_embeddings = False
                else:
                    # 準備文本（標題+內容）
                    texts_for_embedding = [
                        f"{doc['title']} {doc['content']}"[:2000]
                        for doc in docs_to_add
                    ]
                    
                    total_docs = len(texts_for_embedding)
                    
                    # 根據文檔數量調整並行線程數
                    # 小文件用較少線程，大文件用較多線程（但最多 8 個）
                    if total_docs < 50:
                        max_workers = 3
                    elif total_docs < 200:
                        max_workers = 5
                    else:
                        max_workers = 8  # 大文件用更多並行線程
                    
                    embeddings = batch_get_embeddings(
                        texts_for_embedding, 
                        batch_size=5,  # 保留參數但不再使用
                        max_workers=max_workers,
                        show_progress=False
                    )
            except Exception as e:
                embeddings = None
                generate_embeddings = False
        
        # 添加文檔到資料庫
        for i, doc_data in enumerate(docs_to_add):
            embedding = None
            if embeddings and i < len(embeddings) and embeddings[i]:
                embedding = json.dumps(embeddings[i])
            
            doc = Document(
                title=doc_data["title"],
                content=doc_data["content"],
                category="CSV導入",
                source=doc_data["source"],
                embedding=embedding
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

