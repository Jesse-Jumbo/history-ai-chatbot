#!/bin/bash
# 創建 systemd 服務，讓 SAGE 在開機時自動啟動

set -e

SERVICE_NAME="sage-api"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER=$(whoami)

echo "=========================================="
echo "  創建 SAGE systemd 服務"
echo "=========================================="
echo ""

# 檢查是否為 root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 請使用 sudo 執行此腳本"
    exit 1
fi

# 創建服務文件
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SAGE API Server - Face Aging Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$SCRIPT_DIR/venv/bin"
ExecStart=$SCRIPT_DIR/venv/bin/python $SCRIPT_DIR/run_server.py --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ 服務文件已創建: $SERVICE_FILE"
echo ""

# 重新載入 systemd
systemctl daemon-reload
echo "✅ systemd 已重新載入"
echo ""

# 啟用服務
systemctl enable $SERVICE_NAME
echo "✅ 服務已啟用（開機自動啟動）"
echo ""

echo "=========================================="
echo "  服務管理命令："
echo "=========================================="
echo "  啟動服務: sudo systemctl start $SERVICE_NAME"
echo "  停止服務: sudo systemctl stop $SERVICE_NAME"
echo "  重啟服務: sudo systemctl restart $SERVICE_NAME"
echo "  查看狀態: sudo systemctl status $SERVICE_NAME"
echo "  查看日誌: sudo journalctl -u $SERVICE_NAME -f"
echo "  禁用服務: sudo systemctl disable $SERVICE_NAME"
echo ""

