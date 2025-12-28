#!/bin/bash
# SAGE 遠端部署腳本
# 用於在遠端機器上部署 SAGE API 服務

set -e

echo "=========================================="
echo "  SAGE 遠端部署腳本"
echo "=========================================="
echo ""

# 檢查是否在正確的目錄
if [ ! -f "requirements.txt" ]; then
    echo "❌ 錯誤：請在 SAGE 目錄下執行此腳本"
    exit 1
fi

# 1. 檢查 Python 版本
echo "📋 檢查 Python 版本..."
python3 --version || { echo "❌ 需要 Python 3.10+"; exit 1; }

# 2. 檢查 CUDA（可選）
echo ""
echo "📋 檢查 CUDA..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name --format=csv,noheader
    echo "✅ GPU 可用"
else
    echo "⚠️  未檢測到 NVIDIA GPU，將使用 CPU 模式"
fi

# 3. 創建虛擬環境（如果不存在）
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 創建虛擬環境..."
    python3 -m venv venv
fi

# 4. 啟動虛擬環境
echo ""
echo "🔧 啟動虛擬環境..."
source venv/bin/activate

# 5. 升級 pip
echo ""
echo "📦 升級 pip..."
pip install --upgrade pip

# 6. 安裝依賴
echo ""
echo "📦 安裝依賴套件..."
pip install -r requirements.txt

# 7. 檢查並安裝 PyTorch（根據 CUDA 版本）
echo ""
echo "📦 檢查 PyTorch..."
if python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
    echo "✅ PyTorch 已安裝且 CUDA 可用"
else
    echo "⚠️  需要安裝 PyTorch，請根據 CUDA 版本選擇："
    echo "   CUDA 11.8: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118"
    echo "   CUDA 12.1: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121"
    echo "   CUDA 12.4: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124"
fi

# 8. 下載模型（如果不存在）
echo ""
echo "📥 檢查模型檔案..."
if [ ! -d "models/finetune_double_prompt_150_random" ]; then
    echo "⚠️  模型檔案不存在，請執行："
    echo "   python scripts/download_models.py"
else
    echo "✅ 模型檔案已存在"
fi

# 9. 創建必要的目錄
echo ""
echo "📁 創建必要的目錄..."
mkdir -p assets/captured
mkdir -p assets/aged
mkdir -p models

# 10. 配置防火牆
echo ""
echo "🔒 配置防火牆..."
if command -v ufw &> /dev/null; then
    echo "   檢測到 UFW 防火牆"
    UFW_STATUS=$(sudo ufw status | grep -i "狀態" || echo "")
    if echo "$UFW_STATUS" | grep -qi "不活動\|inactive"; then
        echo "   ⚠️  防火牆未啟用，正在啟用..."
        echo "   y" | sudo ufw --force enable || echo "   ⚠️  需要手動啟用：sudo ufw enable"
    fi
    sudo ufw allow 8001/tcp
    echo "   ✅ 已允許端口 8001"
elif command -v firewall-cmd &> /dev/null; then
    echo "   檢測到 firewalld 防火牆"
    sudo firewall-cmd --permanent --add-port=8001/tcp
    sudo firewall-cmd --reload
    echo "   ✅ 已允許端口 8001"
else
    echo "   ⚠️  未檢測到防火牆，請手動配置"
fi

# 11. 獲取本機 IP
echo ""
echo "🌐 網路資訊："
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "   本機 IP: $LOCAL_IP"
echo "   API 地址: http://$LOCAL_IP:8001"
echo "   API 文檔: http://$LOCAL_IP:8001/docs"

echo ""
echo "=========================================="
echo "✅ 部署準備完成！"
echo "=========================================="
echo ""
echo "啟動服務："
echo "  source venv/bin/activate"
echo "  python run_server.py --host 0.0.0.0 --port 8001"
echo ""
echo "或使用 systemd 服務（見 deploy_service.sh）"
echo ""

