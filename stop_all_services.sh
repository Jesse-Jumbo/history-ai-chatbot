#!/bin/bash
# 停止所有服務

echo "停止所有服務..."

# 停止 SAGE API
SAGE_PID=$(lsof -t -i:8001 2>/dev/null)
if [ -n "$SAGE_PID" ]; then
    kill $SAGE_PID
    echo "✅ 已停止 SAGE API (PID: $SAGE_PID)"
else
    echo "⚠️  SAGE API 未運行"
fi

# 停止後端
BACKEND_PID=$(lsof -t -i:8000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID
    echo "✅ 已停止後端 (PID: $BACKEND_PID)"
else
    echo "⚠️  後端未運行"
fi

# 停止前端
FRONTEND_PID=$(lsof -t -i:3000 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID
    echo "✅ 已停止前端 (PID: $FRONTEND_PID)"
else
    echo "⚠️  前端未運行"
fi

echo ""
echo "所有服務已停止"

