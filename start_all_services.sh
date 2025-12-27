#!/bin/bash
# 啟動所有服務（在遠端機器上執行）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  啟動 AI Chatbot 所有服務"
echo "=========================================="
echo ""

# 檢查服務是否已在運行
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0
    else
        return 1
    fi
}

# 啟動 SAGE API
if [ -d "SAGE" ]; then
    if check_port 8001; then
        echo "⚠️  SAGE API (端口 8001) 已在運行"
    else
        echo "1. 啟動 SAGE API..."
        cd SAGE
        source venv/bin/activate
        nohup python run_server.py --host 0.0.0.0 --port 8001 > /tmp/sage.log 2>&1 &
        SAGE_PID=$!
        echo "   ✅ SAGE API 已啟動 (PID: $SAGE_PID)"
        echo "   日誌: tail -f /tmp/sage.log"
        cd ..
    fi
fi

# 等待 SAGE 啟動
sleep 2

# 啟動後端
if check_port 8000; then
    echo "⚠️  後端 (端口 8000) 已在運行"
else
    echo "2. 啟動後端..."
    cd backend
    source venv/bin/activate
    nohup python main.py > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "   ✅ 後端已啟動 (PID: $BACKEND_PID)"
    echo "   日誌: tail -f /tmp/backend.log"
    cd ..
fi

# 等待後端啟動
sleep 2

# 啟動前端
if check_port 3000; then
    echo "⚠️  前端 (端口 3000) 已在運行"
else
    echo "3. 啟動前端..."
    cd frontend
    # 設置環境變數（如果需要）
    export REACT_APP_API_URL=http://localhost:8000
    nohup npm start > /tmp/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "   ✅ 前端已啟動 (PID: $FRONTEND_PID)"
    echo "   日誌: tail -f /tmp/frontend.log"
    cd ..
fi

echo ""
echo "=========================================="
echo "✅ 所有服務已啟動"
echo "=========================================="
echo ""
echo "服務狀態："
echo "  - SAGE API:   http://localhost:8001"
echo "  - 後端 API:   http://localhost:8000"
echo "  - 前端:       http://localhost:3000"
echo ""
echo "從外部訪問（使用遠端機器 IP）："
REMOTE_IP=$(hostname -I | awk '{print $1}')
echo "  - 前端:       http://$REMOTE_IP:3000"
echo ""
echo "查看日誌："
echo "  tail -f /tmp/sage.log"
echo "  tail -f /tmp/backend.log"
echo "  tail -f /tmp/frontend.log"
echo ""
echo "停止服務："
echo "  ./stop_all_services.sh"
echo ""

