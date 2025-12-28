# SAGE 遠端部署指南

本指南說明如何在遠端機器上部署 SAGE API 服務，並從本地電腦透過網路訪問。

## 遠端機器資訊

根據提供的資訊，遠端機器規格：
- **作業系統**: Ubuntu 24.04.3 LTS
- **GPU**: NVIDIA Tegra GB10
- **記憶體**: 128GB
- **磁碟**: 1TB

## 部署步驟

### 1. 準備遠端機器

#### 1.1 連接到遠端機器

使用遠端桌面或 SSH 連接到遠端機器：

```bash
ssh username@remote-machine-ip
```

#### 1.2 上傳 SAGE 專案

將整個 `SAGE/` 資料夾上傳到遠端機器，可以使用以下方法：

**方法一：使用 scp**
```bash
# 從本地電腦執行
scp -r SAGE/ username@remote-machine-ip:/path/to/destination/
```

**方法二：使用 git（如果專案在 Git 上）**
```bash
# 在遠端機器上執行
git clone <your-repo-url>
cd AI-chatbot/SAGE
```

**方法三：使用遠端桌面直接複製**

### 2. 在遠端機器上部署

#### 2.1 進入 SAGE 目錄

```bash
cd /path/to/SAGE
```

#### 2.2 執行部署腳本

```bash
chmod +x deploy_remote.sh
./deploy_remote.sh
```

這個腳本會：
- 檢查 Python 和 CUDA
- 創建虛擬環境
- 安裝所有依賴
- 檢查模型檔案
- 顯示網路資訊

#### 2.3 下載模型（如果尚未下載）

```bash
source venv/bin/activate
python scripts/download_models.py
```

#### 2.4 配置防火牆

允許端口 8001 的訪問：

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 8001/tcp
sudo ufw reload

# 或 CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

### 3. 啟動 SAGE API 服務

#### 方法一：手動啟動（測試用）

```bash
cd /path/to/SAGE
source venv/bin/activate
python run_server.py --host 0.0.0.0 --port 8001
```

服務會顯示：
```
============================================================
  SAGE API Server - Remote Access
============================================================

  Local URL:     http://localhost:8001
  Network URL:   http://<遠端機器IP>:8001
  API Docs:      http://localhost:8001/docs
```

#### 方法二：使用 systemd 服務（推薦，開機自動啟動）

```bash
cd /path/to/SAGE
chmod +x deploy_service.sh
sudo ./deploy_service.sh
sudo systemctl start sage-api
sudo systemctl status sage-api
```

### 4. 測試遠端連接

在本地電腦上測試：

```bash
# 檢查服務狀態
curl http://<遠端機器IP>:8001/status

# 或使用瀏覽器訪問
# http://<遠端機器IP>:8001/docs
```

### 5. 配置本地電腦

#### 5.1 更新環境變數

在本地電腦的 `backend/.env` 中設置：

```env
# SAGE API 配置（遠端機器）
SAGE_API_URL=http://<遠端機器IP>:8001
```

例如，如果遠端機器 IP 是 `192.168.1.100`：

```env
SAGE_API_URL=http://192.168.1.100:8001
```

#### 5.2 測試連接

在本地電腦上測試：

```bash
# 檢查 SAGE API 狀態
curl http://<遠端機器IP>:8001/status

# 或從後端 API 測試
curl http://localhost:8000/api/sage-status
```

## 使用流程

1. **啟動遠端 SAGE 服務**
   - 在遠端機器上啟動 SAGE API（手動或 systemd）

2. **啟動本地後端服務**
   - 在本地電腦上啟動 `backend/main.py`
   - 確保 `.env` 中 `SAGE_API_URL` 指向遠端機器

3. **啟動本地前端**
   - 在本地電腦上啟動前端服務
   - 使用本地攝影機拍照
   - 照片會自動發送到遠端 SAGE 處理

4. **查看結果**
   - 變老後的照片會返回並顯示在前端

## 故障排除

### 問題 1: 無法連接到遠端 SAGE API

**檢查項目：**
1. 確認遠端機器上的 SAGE 服務正在運行
   ```bash
   # 在遠端機器上
   sudo systemctl status sage-api
   # 或
   ps aux | grep run_server
   ```

2. 確認防火牆允許端口 8001
   ```bash
   sudo ufw status
   # 或
   sudo firewall-cmd --list-ports
   ```

3. 確認網路連接
   ```bash
   # 從本地電腦測試
   ping <遠端機器IP>
   telnet <遠端機器IP> 8001
   ```

4. 確認 SAGE API 綁定到 0.0.0.0（不是 127.0.0.1）
   ```bash
   # 檢查服務配置
   cat /etc/systemd/system/sage-api.service
   ```

### 問題 2: 變老處理很慢或失敗

**可能原因：**
1. GPU 未正確配置
   ```bash
   # 在遠端機器上檢查
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. 模型檔案未下載
   ```bash
   ls -lh models/finetune_double_prompt_150_random/
   ```

3. 記憶體不足
   ```bash
   free -h
   ```

### 問題 3: 攝影機無法使用

**注意：** 攝影機是在**本地電腦**上使用的，不是遠端機器。

- 前端使用本地攝影機拍照
- 照片以 base64 編碼發送到本地後端
- 本地後端轉發到遠端 SAGE API
- 遠端 SAGE 處理後返回結果

## 安全建議

1. **使用 HTTPS**（生產環境）
   - 配置反向代理（Nginx）並啟用 SSL
   - 使用 Let's Encrypt 免費證書

2. **限制訪問**
   - 使用防火牆規則限制只有特定 IP 可以訪問
   - 或使用 VPN 連接

3. **認證機制**
   - 在生產環境中添加 API 金鑰認證

## 性能優化

1. **使用 GPU**
   - 確保 PyTorch 正確識別 GPU
   - 使用 `nvidia-smi` 監控 GPU 使用率

2. **調整超時時間**
   - 變老處理可能需要較長時間（1-5 分鐘）
   - 後端已設置 5 分鐘超時

3. **批次處理**
   - 如果需要處理多張照片，考慮實現佇列系統

## 監控和日誌

### 查看服務日誌

```bash
# systemd 服務日誌
sudo journalctl -u sage-api -f

# 或查看最近的日誌
sudo journalctl -u sage-api -n 100
```

### 檢查服務狀態

```bash
sudo systemctl status sage-api
```

## 更新服務

當需要更新 SAGE 代碼時：

```bash
# 1. 停止服務
sudo systemctl stop sage-api

# 2. 更新代碼（git pull 或其他方式）

# 3. 重新安裝依賴（如果需要）
source venv/bin/activate
pip install -r requirements.txt

# 4. 重啟服務
sudo systemctl start sage-api
```

## 聯繫支援

如果遇到問題，請檢查：
1. 服務日誌：`sudo journalctl -u sage-api -f`
2. API 文檔：`http://<遠端機器IP>:8001/docs`
3. 系統資源：`htop`、`nvidia-smi`

