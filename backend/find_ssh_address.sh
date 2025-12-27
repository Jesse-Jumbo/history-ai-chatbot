#!/bin/bash
# 查找 SSH 地址的輔助腳本

echo "=========================================="
echo "  查找 SSH 連接地址"
echo "=========================================="
echo ""

echo "方法 1: 檢查現有的 SSH 配置"
echo "----------------------------------------"
if [ -f ~/.ssh/config ]; then
    echo "找到 SSH 配置文件: ~/.ssh/config"
    echo ""
    echo "已配置的主機："
    grep -E "^Host |HostName " ~/.ssh/config | head -20
    echo ""
    echo "查看完整配置："
    echo "  cat ~/.ssh/config"
else
    echo "未找到 SSH 配置文件"
fi
echo ""

echo "方法 2: 檢查 SSH 連接歷史"
echo "----------------------------------------"
if [ -f ~/.ssh/known_hosts ]; then
    echo "已知的主機（最近連接的）："
    tail -20 ~/.ssh/known_hosts | awk '{print $1}' | cut -d',' -f1 | sort -u
    echo ""
    echo "查看完整列表："
    echo "  cat ~/.ssh/known_hosts | awk '{print \$1}' | cut -d',' -f1 | sort -u"
else
    echo "未找到 known_hosts 文件"
fi
echo ""

echo "方法 3: 檢查 shell 歷史記錄"
echo "----------------------------------------"
echo "最近使用的 SSH 命令："
if [ -f ~/.zsh_history ]; then
    grep -i "ssh.*nckuhis\|ssh.*gx10\|ssh.*192.168" ~/.zsh_history | tail -10
elif [ -f ~/.bash_history ]; then
    grep -i "ssh.*nckuhis\|ssh.*gx10\|ssh.*192.168" ~/.bash_history | tail -10
fi
echo ""

echo "方法 4: 常見的連接方式"
echo "----------------------------------------"
echo "請檢查以下可能的連接方式："
echo ""
echo "1. 公網 IP："
echo "   詢問管理員或查看路由器設定"
echo ""
echo "2. VPN 地址："
echo "   如果使用 VPN，查看 VPN 客戶端顯示的 IP"
echo ""
echo "3. 域名："
echo "   可能有類似 gx10.example.com 的域名"
echo ""
echo "4. 跳板機："
echo "   可能需要先連接到跳板機，再連接到目標機器"
echo ""

echo "方法 5: 測試連接"
echo "----------------------------------------"
echo "如果你知道可能的地址，可以測試："
echo ""
echo "測試 SSH 連接："
echo "  ssh -v nckuhis@<可能的地址>"
echo ""
echo "測試連接（不登入）："
echo "  ssh -o ConnectTimeout=5 nckuhis@<可能的地址> echo '連接成功'"
echo ""

echo "=========================================="
echo "提示："
echo "=========================================="
echo "1. 如果你使用遠端桌面連接，查看遠端桌面客戶端顯示的地址"
echo "2. 詢問系統管理員或 IT 部門"
echo "3. 檢查學校/機構的網路文檔"
echo "4. 查看遠端機器的網路設定（如果可以直接訪問）"
echo ""

