# SSH 隧道設置指南

由於本地電腦和遠端機器不在同一區域網路，無法直接訪問遠端機器的內網 IP。需要使用 SSH 隧道來轉發連接。

## 什麼是 SSH 隧道？

SSH 隧道會將遠端機器的服務（SAGE API）通過 SSH 連接轉發到本地電腦，讓你可以像訪問本地服務一樣訪問遠端服務。

```
本地電腦 ←→ SSH 隧道 ←→ 遠端機器
localhost:8001          localhost:8001 (SAGE API)
```

## 快速開始

### 方法一：使用腳本（推薦）

#### 1. 在背景啟動隧道

```bash
cd backend
chmod +x start_ssh_tunnel.sh stop_ssh_tunnel.sh
./start_ssh_tunnel.sh
```

#### 2. 更新配置

編輯 `backend/.env`，將 SAGE_API_URL 改為本地：

```env
SAGE_API_URL=http://localhost:8001
```

#### 3. 測試連接

```bash
curl http://localhost:8001/status
```

#### 4. 停止隧道

```bash
./stop_ssh_tunnel.sh
```

### 方法二：手動命令

#### 1. 建立 SSH 隧道

```bash
ssh -N -L 8001:localhost:8001 nckuhis@<遠端機器SSH地址>
```

**注意：** 這裡的 `<遠端機器SSH地址>` 是你可以 SSH 連接到遠端機器的地址，可能是：
- 公網 IP
- VPN IP
- 域名

**例如：**
```bash
# 如果遠端機器有公網 IP
ssh -N -L 8001:localhost:8001 nckuhis@123.45.67.89

# 或通過 VPN
ssh -N -L 8001:localhost:8001 nckuhis@vpn.example.com
```

#### 2. 在背景運行（可選）

```bash
ssh -N -f -L 8001:localhost:8001 nckuhis@<遠端機器SSH地址>
```

`-f` 參數讓 SSH 在背景運行。

#### 3. 更新配置

編輯 `backend/.env`：

```env
SAGE_API_URL=http://localhost:8001
```

#### 4. 測試

```bash
curl http://localhost:8001/status
```

## 配置腳本

如果遠端機器的 SSH 地址不是 `192.168.0.236`，需要修改腳本：

編輯 `backend/start_ssh_tunnel.sh`：

```bash
REMOTE_HOST="<你的SSH地址>"  # 改為實際的 SSH 地址
REMOTE_USER="nckuhis"         # SSH 用戶名
```

## 工作原理

SSH 隧道的工作原理：

1. **本地電腦** 建立 SSH 連接到遠端機器
2. SSH 客戶端在本地監聽端口 8001
3. 當有請求發送到 `localhost:8001` 時，SSH 會：
   - 通過 SSH 連接轉發請求到遠端機器
   - 遠端機器將請求發送到 `localhost:8001`（SAGE API）
   - 將回應轉發回本地電腦

## 注意事項

### 1. SSH 連接地址

**重要：** `REMOTE_HOST` 必須是你可以通過 SSH 連接的地址，**不是**內網 IP `192.168.0.236`。

可能的地址：
- 公網 IP（如果有）
- VPN IP（如果通過 VPN 連接）
- 域名（如果有）
- 跳板機地址（如果需要通過跳板機）

### 2. 保持連接

SSH 隧道需要保持 SSH 連接開啟。如果連接斷開，隧道也會中斷。

**保持連接的方法：**

在 `~/.ssh/config` 中添加：

```
Host sage-tunnel
    HostName <遠端機器SSH地址>
    User nckuhis
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

然後使用：

```bash
ssh -N -L 8001:localhost:8001 sage-tunnel
```

### 3. 自動重連

如果連接經常斷開，可以使用 `autossh`：

```bash
# 安裝 autossh
brew install autossh  # macOS
# 或
sudo apt install autossh  # Linux

# 使用 autossh
autossh -M 20000 -N -L 8001:localhost:8001 nckuhis@<遠端機器SSH地址>
```

### 4. 檢查隧道狀態

```bash
# 檢查端口是否被監聽
lsof -i :8001

# 或
netstat -an | grep 8001
```

## 故障排除

### 問題 1: "Connection refused"

**可能原因：**
- 遠端 SAGE API 未運行
- SSH 連接地址錯誤

**解決方法：**
1. 確認可以 SSH 連接到遠端機器
2. 在遠端機器上確認 SAGE API 正在運行

### 問題 2: "Address already in use"

**可能原因：**
- 本地端口 8001 已被佔用

**解決方法：**
```bash
# 查看佔用端口的進程
lsof -i :8001

# 停止佔用的進程，或使用其他端口
ssh -N -L 8002:localhost:8001 nckuhis@<遠端機器SSH地址>
# 然後在 .env 中使用 http://localhost:8002
```

### 問題 3: 隧道經常斷開

**解決方法：**
- 使用 `autossh`（見上方）
- 配置 SSH keepalive（見上方）
- 使用 systemd 服務自動重啟（進階）

## 替代方案

如果 SSH 隧道不方便，可以考慮：

1. **VPN 連接**：將本地電腦和遠端機器連接到同一 VPN
2. **內網穿透工具**：如 ngrok、frp 等
3. **公網 IP + 端口映射**：如果有公網 IP 和路由器管理權限

## 測試連接

設置好隧道後，測試：

```bash
# 測試本地連接
curl http://localhost:8001/status

# 使用測試腳本
cd backend
python test_sage_connection.py
```

應該會看到 SAGE API 的狀態資訊。

