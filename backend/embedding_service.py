import requests
import os
import json
import numpy as np
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ollama API 端點（預設本地）
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# 使用 nomic-embed-text 模型（專為中文優化，體積小，效果好）
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

def get_embedding(text: str) -> Optional[List[float]]:
    """
    使用 Ollama 生成文本的向量嵌入
    
    Args:
        text: 要嵌入的文本
    
    Returns:
        向量嵌入列表，如果失敗則返回 None
    """
    if not text or not text.strip():
        return None
    
    try:
        # 限制文本長度，避免過長
        text = text[:4000]  # Ollama 通常支持更長的文本，但為了穩定性限制長度
        
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30  # 優化：減少超時時間，提升響應速度
        )
        
        if response.status_code != 200:
            return None
        
        result = response.json()
        embedding = result.get("embedding")
        
        if embedding is None:
            return None
        
        return embedding
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    計算兩個向量的餘弦相似度
    
    Args:
        vec1: 第一個向量
        vec2: 第二個向量
    
    Returns:
        相似度分數（0-1之間，1表示完全相同）
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))

def _get_embedding_with_retry(text: str, max_retries: int = 3, retry_delay: float = 1.0) -> Optional[List[float]]:
    """
    生成單個文本的 embedding（帶重試）
    
    Args:
        text: 文本
        max_retries: 最大重試次數
        retry_delay: 重試延遲（秒）
    
    Returns:
        向量嵌入或 None
    """
    embedding = None
    retry_count = 0
    
    while retry_count < max_retries and embedding is None:
        embedding = get_embedding(text)
        if embedding:
            break
        retry_count += 1
        if retry_count < max_retries:
            import time
            time.sleep(retry_delay)
    
    return embedding

def batch_get_embeddings(texts: List[str], batch_size: int = 5, max_workers: int = 5, show_progress: bool = True) -> List[Optional[List[float]]]:
    """
    批量生成向量嵌入（並行處理，失敗自動重試）
    
    Args:
        texts: 文本列表
        batch_size: 批次大小（用於分批提交，避免過載）
        max_workers: 並行工作線程數（建議 3-8，根據 Ollama 服務能力調整）
        show_progress: 是否顯示進度（已移除，不再打印）
    
    Returns:
        向量嵌入列表
    """
    total = len(texts)
    embeddings = [None] * total  # 預分配列表，保持順序
    
    # 使用線程池並行處理
    # 將所有文本分批提交到線程池
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任務
        future_to_index = {
            executor.submit(_get_embedding_with_retry, text): i
            for i, text in enumerate(texts)
        }
        
        # 收集結果（按完成順序，不阻塞）
        completed = 0
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                embedding = future.result()
                embeddings[index] = embedding
                completed += 1
            except Exception as e:
                embeddings[index] = None
    
    return embeddings

def search_by_similarity(
    query_embedding: List[float],
    document_embeddings: List[tuple],  # [(doc_id, embedding), ...]
    top_k: int = 10,
    threshold: float = 0.3
) -> List[tuple]:
    """
    使用向量相似度搜索最相關的文檔（優化版本）
    
    Args:
        query_embedding: 查詢的向量嵌入
        document_embeddings: 文檔向量列表，每個元素是 (doc_id, embedding)
        top_k: 返回前 k 個最相關的文檔
        threshold: 相似度閾值，低於此值的文檔會被過濾
    
    Returns:
        排序後的文檔列表，每個元素是 (similarity_score, doc_id)
    """
    # 優化：使用 numpy 批量計算相似度，提升速度
    import numpy as np
    
    similarities = []
    query_vec = np.array(query_embedding)
    
    for doc_tuple in document_embeddings:
        doc_id = doc_tuple[0]
        doc_embedding_str = doc_tuple[1]
        
        # 解析 embedding（存儲為 JSON 字符串）
        try:
            if isinstance(doc_embedding_str, str):
                doc_embedding = json.loads(doc_embedding_str)
            else:
                doc_embedding = doc_embedding_str
        except:
            continue
        
        if doc_embedding is None:
            continue
        
        # 使用 numpy 快速計算相似度
        doc_vec = np.array(doc_embedding)
        similarity = float(np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)))
        
        if similarity >= threshold:
            similarities.append((similarity, doc_id))
    
    # 按相似度降序排序
    similarities.sort(reverse=True, key=lambda x: x[0])
    
    return similarities[:top_k]

