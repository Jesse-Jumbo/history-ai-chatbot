# 快速部署指南（遠端機器）

## 一鍵部署步驟

### 1. 上傳專案到遠端機器

```bash
# 從本地電腦執行（使用你實際的 SSH 地址）
scp -r AI-chatbot nckuhis@<遠端機器SSH地址>:~/文件/
```

### 2. 在遠端機器上執行部署

```bash
# SSH 連接到遠端機器
ssh nckuhis@<遠端機器SSH地址>

# 進入專案目錄
cd ~/文件/AI-chatbot

# 執行部署腳本
chmod +x deploy_all.sh
./deploy_all.sh
```

### 3. 配置環境變數

#### 後端配置

編輯 `backend/.env`：

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
SAGE_API_URL=http://localhost:8001
GOOGLE_APPLICATION_CREDENTIALS=backend/google-credentials.json
```

#### 前端配置（可選）

如果需要自定義 API 地址，創建 `frontend/.env`：

```env
REACT_APP_API_URL=http://localhost:8000
```

### 4. 配置防火牆

```bash
sudo ufw allow 3000/tcp  # 前端
sudo ufw allow 8000/tcp  # 後端
sudo ufw allow 8001/tcp  # SAGE API
sudo ufw reload
```

### 5. 啟動所有服務

```bash
chmod +x start_all_services.sh stop_all_services.sh
./start_all_services.sh
```

### 6. 訪問應用

在本地瀏覽器打開：

```
http://<遠端機器IP>:3000
```

## 服務管理

### 查看服務狀態

```bash
# 查看端口
netstat -tlnp | grep -E "3000|8000|8001"

# 查看日誌
tail -f /tmp/sage.log
tail -f /tmp/backend.log
tail -f /tmp/frontend.log
```

### 停止所有服務

```bash
./stop_all_services.sh
```

### 重啟服務

```bash
./stop_all_services.sh
sleep 2
./start_all_services.sh
```

## 注意事項

1. **攝影機權限**：攝影機在本地瀏覽器中運行，瀏覽器會請求權限
2. **HTTPS**：生產環境建議使用 HTTPS（需要配置 SSL 證書）
3. **自動啟動**：可以設置 systemd 服務讓服務開機自動啟動（見 DEPLOY_TO_REMOTE.md）

## 故障排除

### 無法訪問前端

1. 檢查服務是否運行：`netstat -tlnp | grep 3000`
2. 檢查防火牆：`sudo ufw status`
3. 查看日誌：`tail -f /tmp/frontend.log`

### API 請求失敗

1. 檢查後端是否運行：`netstat -tlnp | grep 8000`
2. 檢查前端配置的 API 地址是否正確
3. 查看後端日誌：`tail -f /tmp/backend.log`

### SAGE API 連接失敗

1. 檢查 SAGE 是否運行：`netstat -tlnp | grep 8001`
2. 確認 `backend/.env` 中 `SAGE_API_URL=http://localhost:8001`
3. 查看 SAGE 日誌：`tail -f /tmp/sage.log`

