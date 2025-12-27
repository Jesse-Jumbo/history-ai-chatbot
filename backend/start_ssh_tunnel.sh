#!/bin/bash
# 在背景啟動 SSH 隧道

# 配置
REMOTE_HOST="192.168.0.236"  # 遠端機器 IP（SSH 連接用的 IP）
REMOTE_USER="nckuhis"         # SSH 用戶名
REMOTE_PORT="8001"            # 遠端 SAGE API 端口
LOCAL_PORT="8001"              # 本地轉發端口
TUNNEL_PID_FILE="/tmp/sage_tunnel_${LOCAL_PORT}.pid"

echo "=========================================="
echo "  啟動 SSH 隧道（背景模式）"
echo "=========================================="
echo ""

# 檢查是否已有隧道運行
if [ -f "$TUNNEL_PID_FILE" ]; then
    OLD_PID=$(cat "$TUNNEL_PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  SSH 隧道已在運行 (PID: $OLD_PID)"
        echo "   如需重啟，請先執行：./stop_ssh_tunnel.sh"
        exit 0
    else
        rm "$TUNNEL_PID_FILE"
    fi
fi

# 檢查端口是否被佔用
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "❌ 端口 $LOCAL_PORT 已被佔用"
    echo "   正在運行的進程："
    lsof -Pi :$LOCAL_PORT -sTCP:LISTEN
    exit 1
fi

echo "正在建立 SSH 隧道..."
echo "  遠端: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PORT"
echo "  本地: localhost:$LOCAL_PORT"
echo ""

# 在背景啟動 SSH 隧道
ssh -N -f -L $LOCAL_PORT:localhost:$REMOTE_PORT $REMOTE_USER@$REMOTE_HOST

# 獲取進程 ID
sleep 1
TUNNEL_PID=$(lsof -t -i:$LOCAL_PORT 2>/dev/null)
if [ -n "$TUNNEL_PID" ]; then
    echo $TUNNEL_PID > "$TUNNEL_PID_FILE"
    echo "✅ SSH 隧道已啟動 (PID: $TUNNEL_PID)"
    echo ""
    echo "現在可以通過 http://localhost:$LOCAL_PORT 訪問遠端 SAGE API"
    echo ""
    echo "停止隧道："
    echo "  ./stop_ssh_tunnel.sh"
    echo "  或"
    echo "  kill $TUNNEL_PID"
else
    echo "❌ 無法啟動 SSH 隧道"
    echo "   請檢查："
    echo "   1. SSH 連接是否正常"
    echo "   2. 遠端機器是否可訪問"
    echo "   3. 遠端 SAGE API 是否在運行"
    exit 1
fi

