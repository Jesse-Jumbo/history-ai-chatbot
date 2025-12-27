# 如何查找 SSH 連接地址

由於你需要通過 SSH 建立隧道，首先需要知道如何 SSH 連接到遠端機器。

## 快速查找方法

### 1. 執行查找腳本

```bash
cd backend
./find_ssh_address.sh
```

這個腳本會檢查：
- SSH 配置文件
- 連接歷史
- Shell 歷史記錄

### 2. 檢查現有 SSH 配置

```bash
# 查看 SSH 配置
cat ~/.ssh/config

# 查看已知主機
cat ~/.ssh/known_hosts | awk '{print $1}' | cut -d',' -f1 | sort -u
```

### 3. 檢查 Shell 歷史

```bash
# Zsh
grep -i "ssh.*gx10\|ssh.*nckuhis" ~/.zsh_history | tail -20

# Bash
grep -i "ssh.*gx10\|ssh.*nckuhis" ~/.bash_history | tail -20
```

## 常見的 SSH 地址類型

### 1. 公網 IP

如果遠端機器有公網 IP，格式可能是：
```
ssh nckuhis@123.45.67.89
```

**如何查找：**
- 詢問系統管理員
- 查看路由器設定
- 在遠端機器上執行：`curl ifconfig.me` 或 `curl ipinfo.io/ip`

### 2. VPN 地址

如果通過 VPN 連接，可能是：
```
ssh nckuhis@10.0.0.100  # VPN 內網 IP
ssh nckuhis@vpn.example.com  # VPN 域名
```

**如何查找：**
- 查看 VPN 客戶端顯示的 IP
- 查看 VPN 配置文檔
- 詢問 IT 部門

### 3. 學校/機構內網

可能是：
```
ssh nckuhis@gx10-30a0.ncku.edu.tw
ssh nckuhis@192.168.100.50  # 機構內網 IP
```

**如何查找：**
- 查看機構的網路文檔
- 詢問 IT 部門
- 查看遠端桌面客戶端顯示的地址

### 4. 跳板機（Bastion Host）

如果需要通過跳板機：
```
# 先連接到跳板機
ssh user@jump-server.example.com

# 然後從跳板機連接到目標
ssh nckuhis@192.168.0.236
```

**如何查找：**
- 詢問管理員跳板機地址
- 查看機構的網路架構文檔

## 從遠端桌面客戶端查找

如果你使用遠端桌面連接，可以：

1. **查看遠端桌面客戶端**
   - 查看連接設定中顯示的伺服器地址
   - 這通常就是 SSH 可以使用的地址

2. **常見的遠端桌面軟體：**
   - **Windows Remote Desktop**: 查看「電腦名稱」欄位
   - **VNC**: 查看連接地址
   - **TeamViewer**: 查看「夥伴 ID」或連接地址
   - **AnyDesk**: 查看連接地址

## 在遠端機器上查找

如果你已經可以訪問遠端機器（通過遠端桌面），可以在遠端機器上執行：

```bash
# 查看公網 IP
curl ifconfig.me
curl ipinfo.io/ip

# 查看主機名
hostname
hostname -f

# 查看網路介面
ip addr show
# 或
ifconfig

# 查看路由表
ip route
```

## 測試連接

一旦找到可能的地址，測試連接：

```bash
# 基本測試
ssh nckuhis@<可能的地址>

# 測試連接（不登入）
ssh -o ConnectTimeout=5 nckuhis@<可能的地址> echo "連接成功"

# 詳細輸出（查看連接過程）
ssh -v nckuhis@<可能的地址>
```

## 如果找不到 SSH 地址

### 選項 1: 詢問管理員

直接詢問：
- 系統管理員
- IT 部門
- 實驗室管理員

提供資訊：
- 機器名稱：`gx10-30a0`
- 用戶名：`nckuhis`
- 用途：需要 SSH 連接建立隧道

### 選項 2: 檢查機構文檔

查看：
- 機構的網路文檔
- 實驗室的使用手冊
- 系統管理文檔

### 選項 3: 使用其他連接方式

如果無法 SSH，可以考慮：

1. **VPN 連接**
   - 將本地電腦連接到同一 VPN
   - 然後可以直接使用內網 IP `192.168.0.236`

2. **內網穿透工具**
   - ngrok
   - frp
   - 需要管理員協助設置

3. **端口映射**
   - 如果有路由器管理權限
   - 設置端口轉發

## 找到地址後的下一步

一旦找到 SSH 地址：

1. **測試 SSH 連接**
   ```bash
   ssh nckuhis@<SSH地址>
   ```

2. **修改隧道腳本**
   編輯 `backend/start_ssh_tunnel.sh`：
   ```bash
   REMOTE_HOST="<你的SSH地址>"
   ```

3. **啟動隧道**
   ```bash
   ./start_ssh_tunnel.sh
   ```

4. **更新配置**
   編輯 `backend/.env`：
   ```env
   SAGE_API_URL=http://localhost:8001
   ```

## 常見問題

### Q: 我使用遠端桌面，但不知道 SSH 地址

**A:** 遠端桌面和 SSH 通常使用相同的網路地址，但端口不同：
- 遠端桌面：通常是 3389 (RDP) 或 5900 (VNC)
- SSH：通常是 22

嘗試：
```bash
ssh nckuhis@<遠端桌面使用的地址>
```

### Q: 連接需要密碼，可以自動化嗎？

**A:** 可以設置 SSH 金鑰認證：

```bash
# 生成 SSH 金鑰（如果還沒有）
ssh-keygen -t ed25519

# 複製公鑰到遠端機器
ssh-copy-id nckuhis@<SSH地址>
```

之後就不需要輸入密碼了。

### Q: SSH 端口不是 22？

**A:** 在腳本中指定端口：

```bash
ssh -p <端口> -N -L 8001:localhost:8001 nckuhis@<SSH地址>
```

或修改腳本添加 `-p` 參數。

