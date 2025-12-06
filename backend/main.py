from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import csv
import io
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
from database import (
    get_answer_from_db, 
    add_qa_pair, 
    search_documents, 
    add_document,
    get_all_documents,
    batch_add_documents_from_csv,
    init_db
)
from ai_service import generate_answer_with_ai

app = FastAPI(title="歷史系 AI 對話機器人")

# 啟動時初始化資料庫（包括遷移）
@app.on_event("startup")
async def startup_event():
    init_db()

# 全局進度跟踪字典
embedding_progress: Dict[str, Dict] = {}

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    use_ai: bool = True  # 是否使用 AI 增強回答

class QuestionResponse(BaseModel):
    answer: str
    source: str  # "database" 或 "ai" 或 "documents+ai" 或 "none"
    documents_used: Optional[List[dict]] = None  # 使用的文檔（包含來源 ID）
    source_ids: Optional[List[str]] = None  # 來源 ID 列表
    source_details: Optional[List[dict]] = None  # 來源詳細信息：{"source": "來源ID", "doc_titles": ["資料1", "資料2"]}

class DocumentRequest(BaseModel):
    title: str
    content: str
    category: str = "general"
    source: str = ""

class DocumentResponse(BaseModel):
    id: int
    title: str
    category: str
    source: str
    created_at: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "歷史系 AI 對話機器人 API"}

@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    處理使用者問題（RAG 模式）
    1. 從文檔庫搜尋相關資料
    2. 從問答對搜尋
    3. 使用 AI 基於檢索到的資料生成答案
    """
    try:
        # 1. 從文檔庫搜尋相關資料
        # 優先使用向量搜索（embedding），如果失敗則回退到關鍵字搜索
        # 優化：檢索更多文檔以提升準確度，AI 會判斷是否已找到足夠信息
        # 先檢索較多文檔（100個來源），AI 可以提前返回
        documents = search_documents(request.question, limit=100, use_embedding=True)
        
        # 2. 從問答對搜尋
        db_answer = get_answer_from_db(request.question)
        
        # 3. 如果沒有找到相關資料，直接返回不知道
        if not documents and not db_answer:
            return QuestionResponse(
                answer="抱歉，我在資料庫中找不到相關內容，無法回答這個問題。",
                source="none",
                documents_used=None,
                source_ids=None
            )
        
        # 4. 使用 AI 生成答案（如果失败，降级返回文档内容）
        if request.use_ai:
            try:
                ai_answer = await generate_answer_with_ai(
                    question=request.question,
                    context=db_answer if db_answer else None,
                    documents=documents if documents else None
                )
                
                source = "ai"
                source_ids = []
                source_details = []
                if documents:
                    source = "documents+ai"
                    # 收集所有來源和對應的資料標題（包括所有檢索到的，不只是AI使用的）
                    source_ids = [doc.get("source", "") for doc in documents if doc.get("source")]
                    source_details = [
                        {
                            "source": doc.get("source", ""),
                            "doc_titles": doc.get("doc_titles", [])
                        }
                        for doc in documents
                        if doc.get("source")
                    ]
                elif db_answer:
                    source = "database+ai"
                
                return QuestionResponse(
                    answer=ai_answer,
                    source=source,
                    documents_used=documents if documents else None,
                    source_ids=source_ids if source_ids else None,
                    source_details=source_details if source_details else None
                )
            except Exception as e:
                # AI 失败时，降级返回文档内容
                if documents:
                    source_ids = [doc.get("source", "") for doc in documents if doc.get("source")]
                    source_details = [
                        {
                            "source": doc.get("source", ""),
                            "doc_titles": doc.get("doc_titles", [])
                        }
                        for doc in documents
                        if doc.get("source")
                    ]
                    # 合并文档内容作为答案
                    answer_parts = []
                    for doc in documents[:3]:
                        answer_parts.append(f"【來源：{doc.get('source', '未知')}】\n{doc.get('content', '')}")
                    answer = "\n\n".join(answer_parts)
                    
                    return QuestionResponse(
                        answer=answer,
                        source="documents",
                        documents_used=documents,
                        source_ids=source_ids,
                        source_details=source_details if source_details else None
                    )
                # 如果连文档都没有，抛出异常
                raise
        
        # 如果不使用 AI，返回資料庫答案或文檔
        if db_answer:
            return QuestionResponse(
                answer=db_answer,
                source="database",
                source_ids=None
            )
        
        if documents:
            source_ids = [doc.get("source", "") for doc in documents if doc.get("source")]
            source_details = [
                {
                    "source": doc.get("source", ""),
                    "doc_titles": doc.get("doc_titles", [])
                }
                for doc in documents
                if doc.get("source")
            ]
            return QuestionResponse(
                answer=documents[0]["content"],
                source="documents",
                documents_used=documents,
                source_ids=source_ids,
                source_details=source_details if source_details else None
            )
        
        return QuestionResponse(
            answer="抱歉，我目前沒有這個問題的答案。",
            source="none",
            source_ids=None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-qa")
async def add_qa(request: QuestionRequest):
    """新增問答對到資料庫（管理用）"""
    try:
        # 這裡需要提供答案，暫時用 AI 生成
        answer = await generate_answer_with_ai(request.question)
        add_qa_pair(request.question, answer)
        return {"message": "問答對已新增"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents", response_model=dict)
async def create_document(doc: DocumentRequest):
    """新增歷史資料文檔"""
    try:
        doc_id = add_document(
            title=doc.title,
            content=doc.content,
            category=doc.category,
            source=doc.source
        )
        return {"message": "文檔已新增", "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int):
    """獲取單個文檔的詳細內容"""
    try:
        from database import get_document_by_id
        doc = get_document_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文檔不存在")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=List[DocumentResponse])
async def list_documents():
    """獲取所有文檔列表"""
    try:
        docs = get_all_documents()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/clear")
async def clear_all_documents():
    """清空所有文檔和問答對（刪除所有資料）"""
    try:
        from database import SessionLocal, Document, QAPair
        db = SessionLocal()
        try:
            doc_count = db.query(Document).count()
            qa_count = db.query(QAPair).count()
            # 刪除所有文檔
            db.query(Document).delete(synchronize_session=False)
            # 刪除所有問答對
            db.query(QAPair).delete(synchronize_session=False)
            db.commit()
            return {
                "message": f"已清空所有資料，共刪除 {doc_count} 筆文檔和 {qa_count} 筆問答對",
                "doc_count": doc_count,
                "qa_count": qa_count
            }
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失敗：{str(e)}")

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    """刪除指定文檔"""
    try:
        from database import SessionLocal, Document
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="文檔不存在")
            db.delete(doc)
            db.commit()
            return {"message": "文檔已刪除", "id": doc_id}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗：{str(e)}")

@app.delete("/api/documents/source/{source_id}")
async def delete_documents_by_source(source_id: str):
    """根據來源 ID 批量刪除文檔"""
    try:
        from database import SessionLocal, Document
        db = SessionLocal()
        try:
            docs = db.query(Document).filter(Document.source == source_id).all()
            if not docs:
                raise HTTPException(status_code=404, detail=f"找不到來源 '{source_id}' 的文檔")
            count = len(docs)
            for doc in docs:
                db.delete(doc)
            db.commit()
            return {"message": f"已刪除 {count} 筆來源為 '{source_id}' 的文檔", "count": count}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗：{str(e)}")


@app.post("/api/documents/batch")
async def batch_import_documents(documents: List[DocumentRequest]):
    """批量導入文檔"""
    try:
        imported = []
        for doc in documents:
            doc_id = add_document(
                title=doc.title,
                content=doc.content,
                category=doc.category,
                source=doc.source
            )
            imported.append(doc_id)
        return {"message": f"成功導入 {len(imported)} 個文檔", "ids": imported}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """上傳 CSV 文件並批量導入資料
    
    CSV 格式要求：
    - 必須有 'id' 和 'text' 兩個欄位
    - id: 資料名稱（每行的 id 字段會作為該筆資料的標題）
    - text: 內容
    - 整個 CSV 文件會作為一個來源，來源名稱是文件名（不含擴展名）
    """
    try:
        # 獲取文件名（不含擴展名）作為來源 ID
        filename = file.filename or "unknown"
        # 移除 .csv 擴展名
        source_id = filename.replace('.csv', '').replace('.CSV', '')
        
        # 讀取文件內容
        contents = await file.read()
        text = contents.decode('utf-8-sig')  # 處理 BOM
        
        # 解析 CSV
        csv_reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in csv_reader:
            # 檢查必要欄位
            if 'id' not in row or 'text' not in row:
                raise HTTPException(
                    status_code=400, 
                    detail="CSV 文件必須包含 'id' 和 'text' 兩個欄位"
                )
            # id 作為資料名稱，source 使用文件名
            doc_id = row['id'].strip()
            if not doc_id:
                raise HTTPException(
                    status_code=400,
                    detail="CSV 文件中的 'id' 欄位不能為空"
                )
            rows.append({
                "id": doc_id,  # CSV 中的 id 作為資料名稱（title）
                "source": source_id,  # 文件名作為來源 ID
                "text": row['text'].strip()
            })
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV 文件為空或格式錯誤")
        
        # 批量導入（所有資料都屬於同一個來源）
        # 現在支持分批生成 embedding，即使大型文件也可以嘗試生成
        # 如果生成失敗，文檔仍會正常導入，可以稍後通過 API 生成
        count = batch_add_documents_from_csv(rows, generate_embeddings=True)
        
        # 檢查有多少文檔成功生成了 embedding
        from database import SessionLocal, Document
        db = SessionLocal()
        try:
            docs_with_embedding = db.query(Document).filter(
                Document.source == source_id,
                Document.embedding.isnot(None)
            ).count()
            docs_without_embedding = count - docs_with_embedding
        finally:
            db.close()
        
        message = f"成功從 CSV 文件「{source_id}」導入 {count} 筆資料"
        if docs_without_embedding > 0:
            message += f"，其中 {docs_with_embedding} 筆已生成向量嵌入，{docs_without_embedding} 筆尚未生成"
        
        return {
            "message": message,
            "count": count,
            "source": source_id,
            "source_count": 1,  # 只有一個來源（文件名）
            "embeddings_generated": docs_with_embedding,
            "embeddings_pending": docs_without_embedding
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"導入失敗：{str(e)}")

@app.get("/api/documents/embedding-status")
async def get_embedding_status(source_id: str = None):
    """
    查詢指定來源的文檔 embedding 生成狀態
    """
    try:
        from database import SessionLocal, Document
        
        db = SessionLocal()
        try:
            if source_id:
                total = db.query(Document).filter(Document.source == source_id).count()
                with_embedding = db.query(Document).filter(
                    Document.source == source_id,
                    Document.embedding.isnot(None)
                ).count()
            else:
                total = db.query(Document).count()
                with_embedding = db.query(Document).filter(
                    Document.embedding.isnot(None)
                ).count()
            
            return {
                "total": total,
                "with_embedding": with_embedding,
                "without_embedding": total - with_embedding,
                "percentage": round((with_embedding / total * 100) if total > 0 else 0, 2)
            }
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢狀態失敗：{str(e)}")

def generate_embeddings_task(source_id: Optional[str], progress_key: str):
    """後台任務：生成 embedding 並更新進度（失敗自動重試）"""
    try:
        from database import SessionLocal, Document
        from embedding_service import get_embedding
        import json
        import time
        
        db = SessionLocal()
        try:
            # 獲取需要生成 embedding 的文檔
            query = db.query(Document).filter(Document.embedding.is_(None))
            if source_id:
                query = query.filter(Document.source == source_id)
            
            docs = query.all()
            
            if not docs:
                embedding_progress[progress_key] = {
                    "status": "completed",
                    "total": 0,
                    "processed": 0,
                    "percentage": 100
                }
                return
            
            # 準備文本
            texts = []
            doc_ids = []
            for doc in docs:
                if doc.content:
                    text_for_embedding = f"{doc.title} {doc.content}"[:2000]
                    texts.append(text_for_embedding)
                    doc_ids.append(doc.id)
            
            if not texts:
                embedding_progress[progress_key] = {
                    "status": "completed",
                    "total": 0,
                    "processed": 0,
                    "percentage": 100
                }
                return
            
            total_docs = len(texts)
            
            # 初始化進度
            embedding_progress[progress_key] = {
                "status": "processing",
                "total": total_docs,
                "processed": 0,
                "percentage": 0
            }
            
            # 並行生成 embedding（使用線程池）
            max_workers = min(8, total_docs)  # 最多 8 個並行線程，或文檔數量（取較小值）
            embeddings_dict = {}  # {doc_id: embedding}
            
            def process_single_embedding(doc_id, text):
                """處理單個 embedding 生成"""
                from embedding_service import get_embedding
                max_retries = 3
                retry_delay = 1
                
                embedding = None
                retry_count = 0
                
                # 重試邏輯
                while retry_count < max_retries and embedding is None:
                    embedding = get_embedding(text)
                    if embedding:
                        break
                    retry_count += 1
                    if retry_count < max_retries:
                        time.sleep(retry_delay)
                
                return doc_id, embedding
            
            # 使用線程池並行處理
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任務
                future_to_doc_id = {
                    executor.submit(process_single_embedding, doc_id, text): doc_id
                    for doc_id, text in zip(doc_ids, texts)
                }
                
                # 收集結果並更新進度
                completed = 0
                for future in as_completed(future_to_doc_id):
                    try:
                        doc_id, embedding = future.result()
                        if embedding:
                            embeddings_dict[doc_id] = embedding
                        completed += 1
                        
                        # 更新進度
                        percentage = int((completed / total_docs) * 100)
                        embedding_progress[progress_key] = {
                            "status": "processing",
                            "total": total_docs,
                            "processed": completed,
                            "percentage": percentage
                        }
                    except Exception as e:
                        completed += 1
                        percentage = int((completed / total_docs) * 100)
                        embedding_progress[progress_key] = {
                            "status": "processing",
                            "total": total_docs,
                            "processed": completed,
                            "percentage": percentage
                        }
            
            # 批量更新資料庫
            success_count = 0
            for doc_id, embedding in embeddings_dict.items():
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.embedding = json.dumps(embedding)
                    success_count += 1
                    
                    # 每 20 個提交一次
                    if success_count % 20 == 0:
                        db.commit()
            
            db.commit()
            
            # 完成
            embedding_progress[progress_key] = {
                "status": "completed",
                "total": total_docs,
                "processed": total_docs,
                "percentage": 100
            }
            
        except Exception as e:
            embedding_progress[progress_key] = {
                "status": "error",
                "error": str(e),
                "total": 0,
                "processed": 0,
                "percentage": 0
            }
        finally:
            db.close()
    except Exception as e:
        embedding_progress[progress_key] = {
            "status": "error",
            "error": str(e),
            "total": 0,
            "processed": 0,
            "percentage": 0
        }

@app.post("/api/documents/generate-embeddings")
async def generate_embeddings_for_documents(source_id: Optional[str] = None):
    """
    為文檔生成向量嵌入（異步）
    如果提供 source_id，只為該來源的文檔生成
    如果不提供，為所有沒有 embedding 的文檔生成
    
    Returns:
        任務 ID 和初始狀態
    """
    try:
        from database import SessionLocal, Document
        
        db = SessionLocal()
        try:
            # 獲取需要生成 embedding 的文檔數量
            query = db.query(Document).filter(Document.embedding.is_(None))
            if source_id:
                query = query.filter(Document.source == source_id)
            
            total = query.count()
            
            if total == 0:
                return {
                    "message": "所有文檔都已經有 embedding 了" if source_id else "沒有需要生成 embedding 的文檔",
                    "task_id": None,
                    "total": 0
                }
            
            # 創建任務 ID
            import time
            task_id = f"{source_id or 'all'}_{int(time.time())}"
            
            # 啟動後台任務
            thread = Thread(target=generate_embeddings_task, args=(source_id, task_id))
            thread.daemon = True
            thread.start()
            
            return {
                "message": "已開始生成向量嵌入",
                "task_id": task_id,
                "total": total
            }
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"啟動生成任務失敗：{str(e)}")

@app.get("/api/documents/embedding-status")
async def get_embedding_status(source_id: Optional[str] = None):
    """
    獲取 embedding 生成狀態
    如果提供 source_id，只查詢該來源的狀態
    """
    try:
        from database import SessionLocal, Document
        
        db = SessionLocal()
        try:
            query = db.query(Document)
            if source_id:
                query = query.filter(Document.source == source_id)
            
            total = query.count()
            with_embedding = query.filter(Document.embedding.isnot(None)).count()
            without_embedding = total - with_embedding
            
            return {
                "total": total,
                "with_embedding": with_embedding,
                "without_embedding": without_embedding,
                "percentage": round((with_embedding / total * 100) if total > 0 else 0, 2)
            }
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查詢狀態失敗：{str(e)}")

@app.get("/api/documents/embedding-progress/{task_id}")
async def get_embedding_progress(task_id: str):
    """
    獲取 embedding 生成進度
    """
    if task_id not in embedding_progress:
        raise HTTPException(status_code=404, detail="任務不存在或已過期")
    
    progress = embedding_progress[task_id]
    
    # 如果已完成超過 5 分鐘，清理進度記錄
    if progress.get("status") == "completed":
        import time
        if "completed_at" not in progress:
            progress["completed_at"] = time.time()
        elif time.time() - progress["completed_at"] > 300:  # 5 分鐘後清理
            del embedding_progress[task_id]
            raise HTTPException(status_code=404, detail="任務已完成並已清理")
    
    return progress

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

