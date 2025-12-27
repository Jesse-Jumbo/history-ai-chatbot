#!/bin/bash
# 完整部署腳本 - 在遠端機器上執行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  部署 AI Chatbot 到遠端機器"
echo "=========================================="
echo ""

# 1. 設置後端
echo "1. 設置後端環境..."
cd backend
if [ ! -d "venv" ]; then
    echo "   創建虛擬環境..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "   升級 pip..."
pip install --upgrade pip --quiet
echo "   安裝依賴..."
pip install -r requirements.txt --quiet
echo "   ✅ 後端環境設置完成"
cd ..

# 2. 設置前端
echo ""
echo "2. 設置前端環境..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "   安裝依賴..."
    npm install --silent
else
    echo "   依賴已存在，跳過安裝"
fi
echo "   ✅ 前端環境設置完成"
cd ..

# 3. 設置 SAGE（如果存在）
if [ -d "SAGE" ]; then
    echo ""
    echo "3. 檢查 SAGE 環境..."
    cd SAGE
    if [ ! -d "venv" ]; then
        echo "   創建虛擬環境..."
        python3 -m venv venv
    fi
    source venv/bin/activate
    if ! python -c "import torch" 2>/dev/null; then
        echo "   安裝依賴..."
        pip install --upgrade pip --quiet
        pip install -r requirements.txt --quiet
    else
        echo "   SAGE 依賴已安裝"
    fi
    echo "   ✅ SAGE 環境檢查完成"
    cd ..
fi

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 配置環境變數（backend/.env）"
echo "  2. 配置前端 API 地址（frontend/.env 或 Chat.tsx）"
echo "  3. 啟動服務："
echo "     - SAGE: cd SAGE && source venv/bin/activate && python run_server.py --host 0.0.0.0 --port 8001"
echo "     - 後端: cd backend && source venv/bin/activate && python main.py"
echo "     - 前端: cd frontend && npm start"
echo ""

