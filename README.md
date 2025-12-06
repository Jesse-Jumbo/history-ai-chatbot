# 歷史系 AI 對話機器人

一個繁體中文的 QA 小精靈，具備語音輸出、動畫嘴形和字幕顯示功能。

## 功能特色

- 🤖 繁體中文問答系統（支援 Markdown 格式顯示）
- 🎭 2D 吉祥物動畫（嘴形同步）
- 🔊 語音輸出
- 📝 即時字幕顯示
- 💾 本地資料庫儲存
- 🧠 本地 AI 運算（Ollama）
- 🔍 向量嵌入（Embedding）語義搜索
- ⚡ 並行處理優化（快速向量化）
- 📁 CSV 批量資料導入
- 📚 來源追蹤（顯示資料來源 ID 和資料筆數，支援折疊/展開）
- 📊 向量嵌入進度顯示（UI 即時更新）

## 技術棧

### 前端
- React + TypeScript + Vite
- React Markdown（格式渲染）
- CSS 動畫（嘴形控制）
- Web Speech API

### 后端
- Python FastAPI
- SQLite 資料庫
- Ollama（本地 AI）
- 向量嵌入（nomic-embed-text）
- NumPy（向量計算）
- 並行處理（ThreadPoolExecutor）

## 專案結構

```
.
├── frontend/          # React + Vite 前端應用
│   ├── src/
│   │   ├── components/
│   │   │   ├── Mascot.tsx      # 吉祥物組件（嘴形動畫）
│   │   │   ├── Chat.tsx        # 對話界面
│   │   │   ├── Subtitle.tsx    # 字幕組件
│   │   │   └── DocumentManager.tsx  # 資料管理
│   │   ├── App.tsx
│   │   └── main.tsx            # Vite 入口文件
│   ├── index.html              # Vite HTML 模板
│   ├── vite.config.ts          # Vite 配置
│   └── package.json
├── backend/           # FastAPI 後端
│   ├── main.py       # API 服務
│   ├── database.py   # 資料庫操作（向量搜索）
│   ├── ai_service.py # AI 服務（Ollama）
│   ├── embedding_service.py  # 向量嵌入服務
│   ├── migrate_embeddings.py  # 向量嵌入遷移腳本
│   ├── README_EMBEDDING.md    # 向量嵌入說明文檔
│   └── requirements.txt
└── README.md
```

## 使用說明

### 上傳資料（CSV 格式）

在「資料管理」頁面：
- 點擊「📁 上傳 CSV」按鈕
- 選擇 CSV 文件（必須包含 `id` 和 `text` 兩個欄位）
- `id`：資料標題（例如：1933-09-04, A001）
- `text`：內容（歷史資料文字）

**注意**：
- 上傳的 CSV 文件名會作為統一來源 ID，所有資料會歸類到該文件名下
- CSV 中的 `id` 欄位會作為每筆資料的標題
- 上傳後系統會自動為資料生成向量嵌入（Embedding），用於語義搜索
- 如果資料量大，向量嵌入會在後台並行處理，並顯示進度條

**CSV 範例格式：**
```csv
id,text
1933-09-04,照我數年來的習慣，我每朝起床時即去行便...
1933-10-29,今天決定在慈惠院設立病室...
```

### 問答功能

1. 切換到「對話」標籤
2. 輸入問題（例如：「鄭成功何時來台？」或「請幫我總結吳新榮日記的內容」）
3. 系統會：
   - 使用向量嵌入進行語義搜索，檢索所有相關文檔（最多 500 個）
   - AI 會智能判斷是否已找到足夠信息，足夠時提前返回
   - 如果找到，AI 會基於資料回答並顯示來源 ID 和資料筆數
   - 如果找不到，會直接說「找不到相關內容」
   - 如果 AI 超時或失敗，會自動降級返回資料庫中的相關內容
4. 觀看動畫、聆聽語音、閱讀字幕
5. 回答下方會顯示資料來源（可折疊/展開查看詳細來源和資料標題）
6. 回答支援 Markdown 格式（數字列表、加粗、標題等）

### 資料管理

- **查看資料**：在「資料管理」頁面查看所有已上傳的資料
  - 來源可以展開/收起查看詳細資料
  - 顯示每個來源的資料筆數和向量嵌入狀態
- **刪除資料**：可以刪除單筆資料或整個來源的所有資料
- **清空資料**：使用「清空所有資料」按鈕清除所有資料
- **向量嵌入管理**：
  - 上傳 CSV 後會自動生成向量嵌入
  - 可以手動為來源生成向量嵌入（點擊「🔧 生成向量嵌入」按鈕）
  - 查看向量嵌入生成進度（0-100% 進度條）

## 環境要求

### 後端
- Python 3.9+
- Ollama（需安裝並運行）
  - 模型：`qwen2.5:7b`（用於問答）
  - 模型：`nomic-embed-text`（用於向量嵌入）

### 前端
- Node.js 18+
- npm 或 yarn

## 快速開始

### 1. 安裝 Ollama 並下載模型

```bash
# 安裝 Ollama（如果尚未安裝）
# macOS: brew install ollama
# 或訪問 https://ollama.ai 下載

# 下載問答模型
ollama pull qwen2.5:7b

# 下載向量嵌入模型
ollama pull nomic-embed-text

# 啟動 Ollama 服務
ollama serve
```

### 2. 後端設置

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -c "from database import init_db; init_db()"
python main.py
```

### 3. 前端設置

```bash
cd frontend
npm install
npm run dev
```

訪問 `http://localhost:3000` 開始使用。

## 開發費用

✅ 完全免費開源方案
