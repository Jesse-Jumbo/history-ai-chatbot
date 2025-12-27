# Google TTS 憑證申請指南

本指南說明如何申請 Google Cloud Text-to-Speech API 的服務帳戶憑證。

## 步驟 1: 創建 Google Cloud 專案

1. **訪問 Google Cloud Console**
   - 前往：https://console.cloud.google.com/
   - 使用你的 Google 帳號登入

2. **創建新專案**
   - 點擊頂部專案選擇器
   - 點擊「新增專案」
   - 輸入專案名稱（例如：`ai-chatbot-tts`）
   - 點擊「建立」

## 步驟 2: 啟用 Text-to-Speech API

1. **進入 API 庫**
   - 在左側選單選擇「API 和服務」→「程式庫」
   - 或直接訪問：https://console.cloud.google.com/apis/library

2. **搜尋並啟用 Text-to-Speech API**
   - 搜尋「Cloud Text-to-Speech API」
   - 點擊進入
   - 點擊「啟用」按鈕

## 步驟 3: 創建服務帳戶

1. **進入服務帳戶頁面**
   - 左側選單選擇「API 和服務」→「憑證」
   - 或直接訪問：https://console.cloud.google.com/apis/credentials

2. **創建服務帳戶**
   - 點擊「建立憑證」→「服務帳戶」
   - 輸入服務帳戶名稱（例如：`tts-service`）
   - 輸入服務帳戶 ID（自動生成）
   - 點擊「建立並繼續」

3. **設定角色（可選）**
   - 在「授予此服務帳戶對專案的存取權」步驟
   - 可以跳過或選擇「Cloud Text-to-Speech API User」
   - 點擊「繼續」→「完成」

## 步驟 4: 下載憑證金鑰

1. **找到剛創建的服務帳戶**
   - 在「服務帳戶」列表中點擊你剛創建的帳戶

2. **創建金鑰**
   - 切換到「金鑰」標籤
   - 點擊「新增金鑰」→「建立新金鑰」
   - 選擇「JSON」格式
   - 點擊「建立」

3. **保存憑證檔案**
   - 瀏覽器會自動下載 JSON 檔案
   - 檔案名稱類似：`專案名稱-xxxxxxxxxxxx.json`
   - **重要：妥善保管此檔案，不要上傳到 Git**

## 步驟 5: 配置本地環境

1. **放置憑證檔案**
   ```bash
   # 將下載的 JSON 檔案放到專案根目錄或 backend 目錄
   # 例如：
   cp ~/Downloads/ai-chatbot-tts-xxxxx.json backend/google-credentials.json
   ```

2. **更新 .env 檔案**
   
   編輯 `backend/.env`：
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=backend/google-credentials.json
   ```
   
   或使用絕對路徑：
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-credentials.json
   ```

3. **測試配置**
   ```bash
   cd backend
   source venv/bin/activate
   python -c "from google.cloud import texttospeech; print('✅ TTS 憑證配置成功')"
   ```

## 步驟 6: 設定計費（如果需要）

**免費額度：**
- Google Cloud Text-to-Speech 提供**每月 0-4 百萬字符的免費額度**
- 對於個人專案通常足夠使用

**啟用計費帳戶（如果需要更多額度）：**
1. 左側選單選擇「帳單」
2. 點擊「連結帳單帳戶」
3. 按照指示完成設定

**注意：** 即使啟用計費，只要不超過免費額度就不會收費。

## 驗證配置

### 測試 TTS API

```bash
# 在 backend 目錄下
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
if cred_path and os.path.exists(cred_path):
    print(f'✅ 憑證檔案存在: {cred_path}')
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    print('✅ TTS 客戶端創建成功')
else:
    print('❌ 憑證檔案不存在或路徑錯誤')
"
```

### 測試完整 TTS 功能

```bash
# 使用 tts_google.py 測試
python tts_google.py --text "你好，這是測試" --out test.wav
```

## 常見問題

### Q1: 憑證檔案應該放在哪裡？

**建議：**
- 放在 `backend/` 目錄下（已在 .gitignore 中排除）
- 或放在專案根目錄
- **不要**放在會被 Git 追蹤的位置

### Q2: 如何確認憑證是否有效？

```bash
# 測試憑證
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
python -c "from google.cloud import texttospeech; client = texttospeech.TextToSpeechClient(); print('✅ 憑證有效')"
```

### Q3: 遇到「Permission denied」錯誤？

- 確認服務帳戶有「Cloud Text-to-Speech API User」角色
- 確認 API 已啟用
- 確認憑證檔案路徑正確

### Q4: 如何查看使用量？

1. 前往 Google Cloud Console
2. 選擇「API 和服務」→「儀表板」
3. 查看「Cloud Text-to-Speech API」的使用量

## 安全建議

1. **不要將憑證上傳到 Git**
   - 已在 `.gitignore` 中排除 `*-credentials.json`
   - 確認憑證檔案不會被提交

2. **限制憑證權限**
   - 只授予必要的 API 權限
   - 不要使用「Owner」或「Editor」角色

3. **定期輪換憑證**
   - 每 90 天創建新憑證
   - 刪除舊憑證

## 費用說明

**免費額度：**
- 每月前 0-4 百萬字符免費
- 超過後按使用量計費（約 $4/百萬字符）

**估算：**
- 每次對話回答約 100-500 字符
- 每月可免費處理約 8,000-40,000 次對話
- 對個人專案通常足夠

## 參考資源

- [Google Cloud Text-to-Speech 文檔](https://cloud.google.com/text-to-speech/docs)
- [服務帳戶指南](https://cloud.google.com/iam/docs/service-accounts)
- [定價資訊](https://cloud.google.com/text-to-speech/pricing)

