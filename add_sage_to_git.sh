#!/bin/bash
# 將 SAGE 從 submodule 轉換為普通目錄並加入 git

echo "=========================================="
echo "  將 SAGE 加入 Git 倉庫"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

# 檢查 SAGE 是否為 submodule
if [ -f .gitmodules ] && grep -q "SAGE" .gitmodules; then
    echo "檢測到 SAGE 是 git submodule，正在移除..."
    
    # 1. 移除 submodule 配置
    git submodule deinit -f SAGE 2>/dev/null || true
    git rm --cached SAGE 2>/dev/null || true
    
    # 2. 從 .gitmodules 移除
    if [ -f .gitmodules ]; then
        # 如果只有 SAGE，刪除整個文件
        if [ $(grep -c "\[submodule" .gitmodules) -eq 1 ]; then
            rm .gitmodules
        else
            # 否則只移除 SAGE 相關行
            sed -i.bak '/\[submodule "SAGE"\]/,/^$/d' .gitmodules
            rm .gitmodules.bak 2>/dev/null || true
        fi
    fi
    
    # 3. 移除 .git/modules/SAGE（如果存在）
    rm -rf .git/modules/SAGE 2>/dev/null || true
    
    echo "✅ Submodule 已移除"
    echo ""
fi

# 4. 強制加入 SAGE 目錄
echo "正在將 SAGE 加入 Git..."
git add -f SAGE/

# 5. 檢查狀態
echo ""
echo "Git 狀態："
git status --short SAGE/ | head -10

echo ""
echo "=========================================="
echo "✅ 完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  git commit -m 'Add SAGE directory to repository'"
echo ""

