#!/bin/bash
# 快速測試 SAGE API 連接

SAGE_API_URL="${SAGE_API_URL:-http://192.168.0.236:8001}"

echo "=========================================="
echo "  快速測試 SAGE API 連接"
echo "=========================================="
echo ""
echo "SAGE API URL: $SAGE_API_URL"
echo ""

# 解析主機和端口
HOST=$(echo $SAGE_API_URL | sed -E 's|https?://([^:]+):.*|\1|')
PORT=$(echo $SAGE_API_URL | sed -E 's|https?://[^:]+:([0-9]+).*|\1|')

echo "1. 測試基本連接（ping）..."
if ping -c 2 -W 2 $HOST > /dev/null 2>&1; then
    echo "   ✅ 可以 ping 通 $HOST"
else
    echo "   ❌ 無法 ping 通 $HOST"
    echo "   可能不在同一網路或網路不通"
fi
echo ""

echo "2. 測試端口連接..."
if command -v nc > /dev/null; then
    if nc -zv -w 3 $HOST $PORT 2>&1 | grep -q "succeeded"; then
        echo "   ✅ 端口 $PORT 可訪問"
    else
        echo "   ❌ 端口 $PORT 無法訪問"
    fi
elif command -v telnet > /dev/null; then
    timeout 3 telnet $HOST $PORT 2>&1 | grep -q "Connected" && echo "   ✅ 端口 $PORT 可訪問" || echo "   ❌ 端口 $PORT 無法訪問"
else
    echo "   ⚠️  需要 nc 或 telnet 來測試端口"
fi
echo ""

echo "3. 測試 HTTP 連接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$SAGE_API_URL/status" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ HTTP 連接成功（狀態碼: $HTTP_CODE）"
    echo ""
    echo "   服務狀態："
    curl -s --max-time 10 "$SAGE_API_URL/status" | python3 -m json.tool 2>/dev/null || curl -s --max-time 10 "$SAGE_API_URL/status"
else
    echo "   ❌ HTTP 連接失敗（狀態碼: $HTTP_CODE）"
    echo "   嘗試完整請求："
    curl -v --max-time 10 "$SAGE_API_URL/status" 2>&1 | head -20
fi
echo ""

