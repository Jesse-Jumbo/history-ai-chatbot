# Embedding 向量搜索功能說明

## 概述

本系統已實現基於 Embedding 的向量搜索功能，可以大幅提升 RAG（檢索增強生成）的準確性。

## 功能特點

1. **向量嵌入生成**：使用 Ollama 的 `nomic-embed-text` 模型為文檔生成向量嵌入
2. **語義搜索**：使用餘弦相似度進行語義搜索，比關鍵字匹配更準確
3. **自動回退**：如果向量搜索失敗，自動回退到關鍵字搜索
4. **批量處理**：支持批量生成 embedding，提高效率

## 設置步驟

### 1. 安裝依賴

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 下載 Embedding 模型

確保 Ollama 已安裝並運行，然後下載 embedding 模型：

```bash
ollama pull nomic-embed-text
```

### 3. 初始化數據庫

如果數據庫已存在，需要添加 `embedding` 欄位：

```bash
python -c "from database import init_db; init_db()"
```

### 4. 為現有文檔生成 Embedding

如果已有文檔但沒有 embedding，運行遷移腳本：

```bash
python migrate_embeddings.py
```

**注意**：這可能需要較長時間，取決於文檔數量。建議在非高峰時段運行。

### 5. 新文檔自動生成 Embedding

上傳新 CSV 或添加新文檔時，系統會自動生成 embedding（如果 Ollama 可用）。

## 使用方式

### 啟用/禁用向量搜索

在 `main.py` 的 `ask_question` 端點中：

```python
# 啟用向量搜索（預設）
documents = search_documents(request.question, limit=200, use_embedding=True)

# 禁用向量搜索，只使用關鍵字搜索
documents = search_documents(request.question, limit=200, use_embedding=False)
```

### 批量導入時生成 Embedding

在 `batch_add_documents_from_csv` 函數中：

```python
# 生成 embedding（預設，但可能較慢）
count = batch_add_documents_from_csv(rows, generate_embeddings=True)

# 不生成 embedding（更快，但無法使用向量搜索）
count = batch_add_documents_from_csv(rows, generate_embeddings=False)
```

## 配置

### 環境變數

可以在 `.env` 文件中設置：

```env
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=nomic-embed-text
```

### 調整相似度閾值

在 `embedding_service.py` 的 `search_by_similarity` 函數中：

```python
similar_docs = search_by_similarity(
    query_embedding,
    doc_embeddings,
    top_k=search_limit * 3,
    threshold=0.3  # 調整此值：0.0-1.0，越高越嚴格
)
```

## 性能優化

1. **批量生成**：使用 `batch_get_embeddings` 批量生成，比逐個生成快
2. **限制文本長度**：embedding 生成時限制文本長度為 2000 字，避免過長
3. **緩存機制**：embedding 存儲在數據庫中，不需要重複生成

## 故障排除

### 問題：向量搜索失敗

**原因**：
- Ollama 未運行
- `nomic-embed-text` 模型未下載
- 網絡問題

**解決**：
- 檢查 Ollama 是否運行：`ollama list`
- 下載模型：`ollama pull nomic-embed-text`
- 系統會自動回退到關鍵字搜索

### 問題：生成 embedding 很慢

**原因**：
- 文檔數量多
- Ollama 服務器性能不足

**解決**：
- 使用批量生成（已實現）
- 考慮在後台異步生成
- 對於大量文檔，可以分批處理

### 問題：搜索結果不準確

**解決**：
- 調整相似度閾值（`threshold`）
- 檢查 embedding 是否正確生成
- 確保文檔內容質量

## 技術細節

- **模型**：`nomic-embed-text`（專為中文優化，體積小）
- **向量維度**：768 維
- **相似度計算**：餘弦相似度
- **存儲方式**：JSON 字符串存儲在 SQLite 的 `Text` 欄位

## 未來改進

1. 使用專用向量數據庫（如 Chroma、FAISS）提升性能
2. 實現異步生成 embedding
3. 支持多種 embedding 模型
4. 實現混合搜索（向量 + 關鍵字）

