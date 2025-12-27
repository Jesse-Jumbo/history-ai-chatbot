#!/bin/bash
# 設置 SSH 隧道，將遠端 SAGE API 轉發到本地

# 配置
REMOTE_HOST="192.168.0.236"  # 遠端機器 IP（SSH 連接用的 IP，可能是公網 IP 或 VPN IP）
REMOTE_USER="nckuhis"         # SSH 用戶名
REMOTE_PORT="8001"            # 遠端 SAGE API 端口
LOCAL_PORT="8001"              # 本地轉發端口

echo "=========================================="
echo "  設置 SSH 隧道"
echo "=========================================="
echo ""
echo "遠端主機: $REMOTE_USER@$REMOTE_HOST"
echo "遠端端口: $REMOTE_PORT"
echo "本地端口: $LOCAL_PORT"
echo ""
echo "這會將遠端的 SAGE API (端口 $REMOTE_PORT) 轉發到本地的端口 $LOCAL_PORT"
echo ""

# 檢查是否已有 SSH 隧道運行
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  端口 $LOCAL_PORT 已被佔用"
    echo "   正在運行的進程："
    lsof -Pi :$LOCAL_PORT -sTCP:LISTEN
    echo ""
    read -p "是否要終止現有連接並創建新的？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $(lsof -t -i:$LOCAL_PORT) 2>/dev/null
        sleep 1
    else
        echo "取消操作"
        exit 1
    fi
fi

echo "正在建立 SSH 隧道..."
echo "提示：這會在前台運行，按 Ctrl+C 停止"
echo ""

# 建立 SSH 隧道
ssh -N -L $LOCAL_PORT:localhost:$REMOTE_PORT $REMOTE_USER@$REMOTE_HOST

echo ""
echo "SSH 隧道已關閉"

