#!/bin/bash
# 停止 SAGE API 服務

PORT=8001

echo "=========================================="
echo "  停止 SAGE API 服務"
echo "=========================================="
echo ""

# 查找佔用端口的進程
PID=$(lsof -t -i:$PORT 2>/dev/null)

if [ -z "$PID" ]; then
    echo "⚠️  端口 $PORT 沒有被佔用"
    echo "   服務可能已經停止"
    exit 0
fi

echo "找到進程: PID=$PID"
echo ""

# 顯示進程資訊
echo "進程詳情："
ps -p $PID -o pid,ppid,cmd --no-headers
echo ""

# 詢問確認
read -p "是否要停止此進程？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "取消操作"
    exit 0
fi

# 停止進程
echo "正在停止進程..."
kill $PID

# 等待進程結束
sleep 2

# 檢查是否還在運行
if ps -p $PID > /dev/null 2>&1; then
    echo "⚠️  進程仍在運行，強制停止..."
    kill -9 $PID
    sleep 1
fi

# 再次檢查
if ps -p $PID > /dev/null 2>&1; then
    echo "❌ 無法停止進程，請手動處理"
    exit 1
else
    echo "✅ 服務已停止"
    echo ""
    echo "確認端口狀態："
    lsof -i:$PORT 2>/dev/null || echo "   端口 $PORT 已釋放"
fi

