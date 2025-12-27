# 遠端機器完整部署指南

將整個專案（前端 + 後端 + SAGE）部署到遠端機器，通過瀏覽器訪問。

## 架構說明

```
本地瀏覽器 → 遠端機器
            ├── 前端 (React) - 端口 3000
            ├── 後端 (FastAPI) - 端口 8000
            └── SAGE API - 端口 8001
```

**優點：**
- 不需要 SSH 隧道
- 所有服務在同一機器，連接更快
- 攝影機仍可在本地使用（瀏覽器在本地運行）

## 部署步驟

### 1. 準備遠端機器

#### 1.1 上傳專案到遠端機器

**方法一：使用 scp（從本地電腦執行）**

```bash
# 在本地電腦上
cd /Users/jesse/Documents/NCKU/歷史系
scp -r AI-chatbot nckuhis@<遠端機器SSH地址>:~/文件/
```

**方法二：使用 git（如果專案在 Git 上）**

```bash
# 在遠端機器上
cd ~/文件
git clone <your-repo-url>
cd AI-chatbot
```

**方法三：使用遠端桌面直接複製**

### 2. 在遠端機器上設置環境

#### 2.1 安裝 Node.js（前端需要）

```bash
# 檢查是否已安裝
node --version
npm --version

# 如果沒有，安裝 Node.js（Ubuntu）
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 或使用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
```

#### 2.2 設置後端環境

```bash
cd ~/文件/AI-chatbot/backend

# 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2.3 設置前端環境

```bash
cd ~/文件/AI-chatbot/frontend

# 安裝依賴
npm install
```

#### 2.4 設置 SAGE（如果還沒設置）

```bash
cd ~/文件/AI-chatbot/SAGE

# 執行部署腳本
chmod +x deploy_remote.sh
./deploy_remote.sh

# 下載模型（如果需要）
source venv/bin/activate
python scripts/download_models.py
```

### 3. 配置環境變數

#### 3.1 後端配置

編輯 `backend/.env`：

```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite

# SAGE API（現在在同一機器，使用 localhost）
SAGE_API_URL=http://localhost:8001

# Google TTS 憑證
GOOGLE_APPLICATION_CREDENTIALS=backend/google-credentials.json
```

#### 3.2 前端配置

編輯 `frontend/src/components/Chat.tsx`，修改 API 地址：

```typescript
// 如果通過公網 IP 訪問，使用遠端機器的 IP
const API_BASE_URL = 'http://<遠端機器IP>:8000';

// 或如果通過域名訪問
const API_BASE_URL = 'http://your-domain.com:8000';
```

**更好的方式：使用環境變數**

創建 `frontend/.env`：

```env
REACT_APP_API_URL=http://localhost:8000
```

然後在 `Chat.tsx` 中：

```typescript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### 4. 配置防火牆

```bash
# 允許前端端口
sudo ufw allow 3000/tcp

# 允許後端端口
sudo ufw allow 8000/tcp

# 允許 SAGE API 端口（如果從外部訪問）
sudo ufw allow 8001/tcp

# 重新載入
sudo ufw reload
```

### 5. 啟動服務

#### 5.1 啟動 SAGE API

```bash
cd ~/文件/AI-chatbot/SAGE
source venv/bin/activate
python run_server.py --host 0.0.0.0 --port 8001
```

或使用 systemd 服務（見下方「自動啟動設置」）。

#### 5.2 啟動後端

```bash
cd ~/文件/AI-chatbot/backend
source venv/bin/activate
python main.py
```

後端會自動綁定到 `0.0.0.0:8000`，可以從外部訪問。

#### 5.3 啟動前端

```bash
cd ~/文件/AI-chatbot/frontend
npm start
```

前端會綁定到 `0.0.0.0:3000`。

### 6. 訪問應用

在本地瀏覽器打開：

```
http://<遠端機器IP>:3000
```

或如果配置了域名：

```
http://your-domain.com:3000
```

## 自動啟動設置（使用 systemd）

### 創建後端服務

創建 `/etc/systemd/system/ai-chatbot-backend.service`：

```ini
[Unit]
Description=AI Chatbot Backend
After=network.target

[Service]
Type=simple
User=nckuhis
WorkingDirectory=/home/nckuhis/文件/AI-chatbot/backend
Environment="PATH=/home/nckuhis/文件/AI-chatbot/backend/venv/bin"
ExecStart=/home/nckuhis/文件/AI-chatbot/backend/venv/bin/python /home/nckuhis/文件/AI-chatbot/backend/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 創建前端服務

創建 `/etc/systemd/system/ai-chatbot-frontend.service`：

```ini
[Unit]
Description=AI Chatbot Frontend
After=network.target

[Service]
Type=simple
User=nckuhis
WorkingDirectory=/home/nckuhis/文件/AI-chatbot/frontend
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 啟用服務

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-chatbot-backend
sudo systemctl enable ai-chatbot-frontend
sudo systemctl enable sage-api

sudo systemctl start ai-chatbot-backend
sudo systemctl start ai-chatbot-frontend
sudo systemctl start sage-api
```

### 查看服務狀態

```bash
sudo systemctl status ai-chatbot-backend
sudo systemctl status ai-chatbot-frontend
sudo systemctl status sage-api
```

## 使用 Nginx 反向代理（可選，推薦）

如果不想使用端口號，可以設置 Nginx 反向代理：

### 安裝 Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 配置 Nginx

創建 `/etc/nginx/sites-available/ai-chatbot`：

```nginx
server {
    listen 80;
    server_name <你的域名或IP>;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 後端 API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SAGE API（如果需要從外部訪問）
    location /sage {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

啟用配置：

```bash
sudo ln -s /etc/nginx/sites-available/ai-chatbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

然後可以通過 `http://<域名或IP>` 訪問，不需要端口號。

## 攝影機權限處理

**重要：** 攝影機在本地瀏覽器中運行，所以：

1. **瀏覽器會請求攝影機權限**（在本地電腦上）
2. **攝影機數據會通過網路發送到遠端後端**
3. **不需要在遠端機器上配置攝影機**

確保：
- 使用 HTTPS（生產環境）或允許 HTTP 訪問攝影機（開發環境）
- 瀏覽器允許攝影機權限

## 安全建議

### 1. 使用 HTTPS

```bash
# 安裝 Certbot
sudo apt install certbot python3-certbot-nginx

# 獲取 SSL 證書
sudo certbot --nginx -d your-domain.com
```

### 2. 限制訪問

在 Nginx 配置中添加 IP 白名單：

```nginx
location / {
    allow 192.168.1.0/24;  # 允許特定網段
    deny all;
    proxy_pass http://localhost:3000;
}
```

### 3. 設置認證（可選）

使用 HTTP Basic Auth：

```nginx
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:3000;
}
```

## 故障排除

### 問題 1: 無法訪問前端

**檢查：**
```bash
# 檢查服務是否運行
sudo systemctl status ai-chatbot-frontend

# 檢查端口
netstat -tlnp | grep 3000

# 檢查防火牆
sudo ufw status
```

### 問題 2: API 請求失敗

**檢查：**
```bash
# 檢查後端日誌
sudo journalctl -u ai-chatbot-backend -f

# 測試 API
curl http://localhost:8000/api/sage-status
```

### 問題 3: 攝影機無法使用

**可能原因：**
- 瀏覽器不允許 HTTP 訪問攝影機（需要 HTTPS）
- 攝影機權限被拒絕

**解決方法：**
- 開發環境：使用 `http://localhost:3000`（本地訪問）
- 生產環境：使用 HTTPS

## 快速部署腳本

創建 `deploy_all.sh`：

```bash
#!/bin/bash
# 完整部署腳本

set -e

echo "=========================================="
echo "  部署 AI Chatbot 到遠端機器"
echo "=========================================="

# 1. 設置後端
echo "1. 設置後端..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# 2. 設置前端
echo "2. 設置前端..."
cd frontend
npm install
cd ..

# 3. 設置 SAGE
echo "3. 設置 SAGE..."
cd SAGE
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "啟動服務："
echo "  1. SAGE: cd SAGE && source venv/bin/activate && python run_server.py --host 0.0.0.0 --port 8001"
echo "  2. 後端: cd backend && source venv/bin/activate && python main.py"
echo "  3. 前端: cd frontend && npm start"
echo ""
```

## 總結

將整個專案部署到遠端機器的優點：
- ✅ 不需要 SSH 隧道
- ✅ 所有服務在同一機器，連接更快
- ✅ 可以通過瀏覽器直接訪問
- ✅ 攝影機仍可在本地使用

缺點：
- ⚠️ 需要遠端機器有足夠資源
- ⚠️ 需要配置防火牆和網路
- ⚠️ 如果遠端機器重啟，需要確保服務自動啟動

