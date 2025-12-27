#!/bin/bash
# 停止 SSH 隧道

LOCAL_PORT="8001"
TUNNEL_PID_FILE="/tmp/sage_tunnel_${LOCAL_PORT}.pid"

echo "停止 SSH 隧道..."

if [ -f "$TUNNEL_PID_FILE" ]; then
    PID=$(cat "$TUNNEL_PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ 已停止 SSH 隧道 (PID: $PID)"
        rm "$TUNNEL_PID_FILE"
    else
        echo "⚠️  進程不存在，清理 PID 文件"
        rm "$TUNNEL_PID_FILE"
    fi
else
    # 嘗試通過端口查找
    PID=$(lsof -t -i:$LOCAL_PORT 2>/dev/null)
    if [ -n "$PID" ]; then
        kill $PID
        echo "✅ 已停止 SSH 隧道 (PID: $PID)"
    else
        echo "⚠️  未找到運行中的 SSH 隧道"
    fi
fi

