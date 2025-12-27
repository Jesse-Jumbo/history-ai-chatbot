# 故障排除指南

## SAGE API 連接問題

### 症狀
- 拍照後出現 "變老處理失敗" 錯誤
- 後端返回 500 錯誤
- 瀏覽器控制台顯示 "Request failed with status code 500"

### 診斷步驟

#### 1. 檢查 SAGE API 配置

確認 `backend/.env` 中的配置：

```env
SAGE_API_URL=http://localhost:8001
```

如果 SAGE 在遠端機器，使用遠端 IP：

```env
SAGE_API_URL=http://192.168.1.100:8001
```

#### 2. 測試連接

在後端目錄執行：

```bash
cd backend
source venv/bin/activate
python test_sage_connection.py
```

這個腳本會：
- 測試基本連接
- 顯示 SAGE API 狀態
- 提供詳細的錯誤訊息和解決建議

#### 3. 檢查 SAGE API 服務狀態

**如果 SAGE 在本機：**

```bash
# 檢查服務是否運行
curl http://localhost:8001/status

# 或訪問 API 文檔
open http://localhost:8001/docs
```

**如果 SAGE 在遠端機器：**

```bash
# 在遠端機器上檢查
ssh username@remote-ip
sudo systemctl status sage-api

# 或手動檢查
ps aux | grep run_server
```

#### 4. 檢查後端日誌

啟動後端時，會自動檢查 SAGE API 連接：

```bash
cd backend
python main.py
```

查看啟動時的連接檢查訊息。

#### 5. 使用 API 測試端點

在瀏覽器或使用 curl：

```bash
# 測試 SAGE API 狀態
curl http://localhost:8000/api/sage-status
```

### 常見問題和解決方法

#### 問題 1: "無法連接到 SAGE API"

**可能原因：**
- SAGE API 服務未啟動
- SAGE_API_URL 配置錯誤
- 防火牆阻擋

**解決方法：**

1. **確認 SAGE API 是否運行**
   ```bash
   # 如果在本機
   curl http://localhost:8001/status
   
   # 如果在遠端
   curl http://<遠端IP>:8001/status
   ```

2. **檢查配置**
   ```bash
   # 查看當前配置
   cat backend/.env | grep SAGE_API_URL
   ```

3. **啟動 SAGE API**
   ```bash
   # 在 SAGE 目錄
   cd SAGE
   source venv/bin/activate
   python run_server.py --host 0.0.0.0 --port 8001
   ```

#### 問題 2: "SAGE API 返回錯誤 500"

**可能原因：**
- SAGE API 內部錯誤
- 圖片格式或大小問題
- GPU 或模型問題

**解決方法：**

1. **檢查 SAGE API 日誌**
   ```bash
   # 如果使用 systemd
   sudo journalctl -u sage-api -f
   
   # 或查看手動啟動的終端輸出
   ```

2. **測試 SAGE API 直接調用**
   ```bash
   # 使用 curl 測試
   curl -X POST http://localhost:8001/age/photo \
     -H "Content-Type: application/json" \
     -d '{"image_base64": "base64_encoded_image", "target_age": 75, "mock": false}'
   ```

3. **嘗試使用 Mock 模式**
   ```javascript
   // 在前端，暫時使用 mock 模式測試
   mock: true
   ```

#### 問題 3: "連接超時"

**可能原因：**
- 變老處理時間過長（正常可能需要 1-5 分鐘）
- 網路連接不穩定
- SAGE API 服務響應慢

**解決方法：**

1. **增加超時時間**（已在代碼中設置為 5 分鐘）
2. **檢查網路連接**
3. **使用 Mock 模式測試**（更快）

#### 問題 4: 遠端連接問題

**可能原因：**
- 防火牆未配置
- 網路不可達
- SAGE API 未綁定到 0.0.0.0

**解決方法：**

1. **確認 SAGE API 綁定**
   ```bash
   # 在遠端機器上，確認使用 0.0.0.0
   python run_server.py --host 0.0.0.0 --port 8001
   ```

2. **配置防火牆**
   ```bash
   # 在遠端機器上
   sudo ufw allow 8001/tcp
   sudo ufw reload
   ```

3. **測試網路連接**
   ```bash
   # 從本地電腦測試
   ping <遠端IP>
   telnet <遠端IP> 8001
   ```

### 調試技巧

#### 1. 啟用詳細日誌

在後端啟動時，會自動顯示連接檢查結果。

#### 2. 使用瀏覽器開發者工具

- 打開瀏覽器開發者工具（F12）
- 查看 Network 標籤
- 檢查 `/api/age-photo` 請求的詳細錯誤

#### 3. 檢查後端終端輸出

後端會顯示詳細的錯誤訊息，包括：
- 連接錯誤類型
- SAGE API URL
- 具體錯誤原因

### 快速檢查清單

- [ ] SAGE API 服務正在運行
- [ ] `backend/.env` 中 `SAGE_API_URL` 配置正確
- [ ] 可以訪問 `http://<SAGE_API_URL>/status`
- [ ] 防火牆允許端口 8001（如果使用遠端）
- [ ] 網路連接正常
- [ ] 執行 `python test_sage_connection.py` 測試通過

### 獲取幫助

如果問題仍然存在，請提供：

1. **後端啟動時的連接檢查輸出**
2. **執行 `test_sage_connection.py` 的結果**
3. **瀏覽器控制台的錯誤訊息**
4. **SAGE API 的日誌**（如果可用）

