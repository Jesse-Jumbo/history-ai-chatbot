#!/bin/bash
# 快速修復防火牆配置

echo "=========================================="
echo "  修復防火牆配置"
echo "=========================================="
echo ""

# 檢查 UFW
if command -v ufw &> /dev/null; then
    echo "📋 檢測到 UFW 防火牆"
    
    # 檢查狀態
    UFW_STATUS=$(sudo ufw status | head -1)
    echo "   當前狀態: $UFW_STATUS"
    
    # 如果未啟用，啟用它
    if echo "$UFW_STATUS" | grep -qi "不活動\|inactive"; then
        echo ""
        echo "⚠️  防火牆未啟用，正在啟用..."
        echo "y" | sudo ufw --force enable
        echo "✅ 防火牆已啟用"
    else
        echo "✅ 防火牆已啟用"
    fi
    
    # 允許端口 8001
    echo ""
    echo "📝 配置端口 8001..."
    sudo ufw allow 8001/tcp
    echo "✅ 已允許端口 8001"
    
    # 顯示狀態
    echo ""
    echo "📊 當前防火牆規則："
    sudo ufw status numbered
    
elif command -v firewall-cmd &> /dev/null; then
    echo "📋 檢測到 firewalld 防火牆"
    
    # 允許端口 8001
    sudo firewall-cmd --permanent --add-port=8001/tcp
    sudo firewall-cmd --reload
    echo "✅ 已允許端口 8001"
    
    # 顯示狀態
    echo ""
    echo "📊 當前開放端口："
    sudo firewall-cmd --list-ports
    
else
    echo "❌ 未檢測到防火牆工具（ufw 或 firewalld）"
    echo "   請手動配置防火牆允許端口 8001"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 防火牆配置完成"
echo "=========================================="
echo ""
echo "測試連接："
echo "  curl http://$(hostname -I | awk '{print $1}'):8001/status"
echo ""

