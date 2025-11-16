# 歷史系 AI 對話機器人

一個繁體中文的 QA 小精靈，具備語音輸出、動畫嘴形和字幕顯示功能。

## 功能特色

- 🤖 繁體中文問答系統
- 🎭 2D 吉祥物動畫（嘴形同步）
- 🔊 語音輸出
- 📝 即時字幕顯示
- 💾 本地資料庫儲存
- 🧠 本地 AI 運算（Ollama）
- 📁 CSV 批量資料導入
- 📚 來源追蹤（顯示資料來源 ID）

## 技術棧

### 前端
- React + TypeScript + Vite
- CSS 動畫（嘴形控制）
- Web Speech API

### 后端
- Python FastAPI
- SQLite 資料庫
- Ollama（本地 AI）

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
│   ├── database.py   # 資料庫操作
│   ├── ai_service.py # AI 服務（Ollama）
│   └── requirements.txt
└── README.md
```

## 使用說明

### 上傳資料（CSV 格式）

在「資料管理」頁面：
- 點擊「📁 上傳 CSV」按鈕
- 選擇 CSV 文件（必須包含 `id` 和 `text` 兩個欄位）
- `id`：來源 ID（例如：A001, B002）
- `text`：內容（歷史資料文字）

**注意**：上傳的 CSV 文件名會作為統一來源 ID，所有資料會歸類到該文件名下。

**CSV 範例格式：**
```csv
id,text
A001,鄭成功於1661年率軍來台...
A002,日治時期從1895年開始...
```

### 問答功能

1. 切換到「對話」標籤
2. 輸入問題（例如：「鄭成功何時來台？」）
3. 系統會：
   - 從資料庫搜尋相關內容
   - 如果找到，AI 會基於資料回答並顯示來源 ID
   - 如果找不到，會直接說「找不到相關內容」
   - 如果 AI 超時或失敗，會自動降級返回資料庫中的相關內容
4. 觀看動畫、聆聽語音、閱讀字幕
5. 回答下方會顯示資料來源（來源 ID）

### 資料管理

- **查看資料**：在「資料管理」頁面查看所有已上傳的資料
- **刪除資料**：可以刪除單筆資料或整個來源的所有資料
- **清空資料**：使用「清空所有資料」按鈕清除所有資料

## 開發費用

✅ 完全免費開源方案
