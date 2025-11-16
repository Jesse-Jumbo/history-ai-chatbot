"""
為現有文檔生成向量嵌入的遷移腳本
運行此腳本可以為資料庫中沒有 embedding 的文檔生成向量嵌入
"""
from database import SessionLocal, Document, init_db
from embedding_service import get_embedding
import json

def migrate_embeddings(max_workers: int = 5):
    """
    為所有沒有 embedding 的文檔生成向量嵌入（並行處理）
    
    Args:
        max_workers: 並行線程數（建議 3-8）
    """
    db = SessionLocal()
    try:
        # 獲取所有沒有 embedding 的文檔
        docs_without_embedding = db.query(Document).filter(
            Document.embedding.is_(None)
        ).all()
        
        total = len(docs_without_embedding)
        if total == 0:
            print("所有文檔都已經有 embedding 了！")
            return
        
        print(f"找到 {total} 個沒有 embedding 的文檔")
        print("開始分批生成 embedding...\n")
        
        from embedding_service import batch_get_embeddings
        
        # 準備文本
        texts = []
        doc_ids = []
        for doc in docs_without_embedding:
            if doc.content:
                text_for_embedding = f"{doc.title} {doc.content}"[:2000]
                texts.append(text_for_embedding)
                doc_ids.append(doc.id)
        
        if not texts:
            print("沒有需要處理的文檔內容")
            return
        
        # 並行生成 embedding
        embeddings = batch_get_embeddings(texts, max_workers=max_workers, show_progress=True)
        
        # 更新資料庫
        count = 0
        for i, (doc_id, embedding) in enumerate(zip(doc_ids, embeddings)):
            if embedding:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc:
                    doc.embedding = json.dumps(embedding)
                    count += 1
                    
                    # 每 10 個提交一次
                    if count % 10 == 0:
                        db.commit()
        
        db.commit()
        print(f"\n完成！共為 {count}/{len(texts)} 個文檔生成了 embedding")
        if count < len(texts):
            print(f"警告：{len(texts) - count} 個文檔的 embedding 生成失敗")
            print("您可以再次運行此腳本來重試失敗的文檔")
        
    except Exception as e:
        db.rollback()
        print(f"遷移失敗: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("開始為現有文檔生成向量嵌入...")
    print("這可能需要一些時間，請耐心等待...")
    migrate_embeddings()

