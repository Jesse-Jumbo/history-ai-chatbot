# SAGE 遠端部署快速指南

## 快速開始（5 分鐘）

### 在遠端機器上

1. **上傳 SAGE 資料夾到遠端機器**
   ```bash
   # 使用 scp（從本地電腦執行）
   scp -r SAGE/ username@remote-ip:/home/username/
   ```

2. **連接到遠端機器並部署**
   ```bash
   ssh username@remote-ip
   cd SAGE
   chmod +x deploy_remote.sh
   ./deploy_remote.sh
   ```

3. **下載模型（如果尚未下載）**
   ```bash
   source venv/bin/activate
   python scripts/download_models.py
   ```

4. **配置防火牆**
   ```bash
   sudo ufw allow 8001/tcp
   sudo ufw reload
   ```

5. **啟動服務（選擇一種方式）**

   **方式 A：手動啟動（測試用）**
   ```bash
   source venv/bin/activate
   python run_server.py --host 0.0.0.0 --port 8001
   ```

   **方式 B：systemd 服務（推薦，開機自動啟動）**
   ```bash
   chmod +x deploy_service.sh
   sudo ./deploy_service.sh
   sudo systemctl start sage-api
   ```

6. **獲取遠端機器 IP**
   ```bash
   hostname -I | awk '{print $1}'
   # 記下這個 IP，例如：192.168.1.100
   ```

### 在本地電腦上

1. **更新環境變數**
   
   編輯 `backend/.env`：
   ```env
   SAGE_API_URL=http://<遠端機器IP>:8001
   ```
   
   例如：
   ```env
   SAGE_API_URL=http://192.168.1.100:8001
   ```

2. **測試連接**
   ```bash
   # 測試遠端 SAGE API
   curl http://<遠端機器IP>:8001/status
   
   # 或從後端測試
   curl http://localhost:8000/api/sage-status
   ```

3. **啟動本地服務**
   ```bash
   # 後端
   cd backend
   source venv/bin/activate
   python main.py
   
   # 前端（另一個終端）
   cd frontend
   npm run dev
   ```

4. **使用**
   - 打開瀏覽器訪問前端
   - 點擊「開始拍照」
   - 使用本地攝影機拍照
   - 照片會自動發送到遠端處理並顯示結果

## 常用命令

### 遠端機器

```bash
# 查看服務狀態
sudo systemctl status sage-api

# 啟動服務
sudo systemctl start sage-api

# 停止服務
sudo systemctl stop sage-api

# 重啟服務
sudo systemctl restart sage-api

# 查看日誌
sudo journalctl -u sage-api -f

# 檢查 GPU
nvidia-smi

# 檢查端口
netstat -tlnp | grep 8001
```

### 本地電腦

```bash
# 測試遠端連接
curl http://<遠端IP>:8001/status

# 檢查後端配置
cat backend/.env | grep SAGE_API_URL
```

## 故障排除

### 無法連接？

1. **檢查服務是否運行**
   ```bash
   # 在遠端機器上
   sudo systemctl status sage-api
   ```

2. **檢查防火牆**
   ```bash
   # 在遠端機器上
   sudo ufw status
   ```

3. **檢查網路**
   ```bash
   # 從本地電腦
   ping <遠端IP>
   telnet <遠端IP> 8001
   ```

### 處理很慢？

- 檢查 GPU 是否可用：`nvidia-smi`
- 檢查模型是否下載：`ls models/finetune_double_prompt_150_random/`
- 變老處理通常需要 1-5 分鐘，這是正常的

## 架構說明

```
本地電腦                   遠端機器
┌─────────┐              ┌─────────┐
│ 前端    │              │         │
│ (攝影機)│              │  SAGE   │
└────┬────┘              │  API    │
     │                   │  (GPU)  │
     │ 拍照              │         │
     ▼                   │         │
┌─────────┐              │         │
│ 後端    │─────────────▶│         │
│ (代理)  │  變老請求    │         │
└─────────┘              └─────────┘
     │                         │
     │  返回變老照片            │
     ◀─────────────────────────┘
     │
     ▼
   顯示結果
```

**重點：**
- 攝影機在**本地電腦**上使用
- 變老處理在**遠端機器**上執行（使用 GPU）
- 照片通過網路傳輸

