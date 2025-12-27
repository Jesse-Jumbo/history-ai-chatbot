#!/usr/bin/env python3
"""計算上傳文件限制說明"""
import os

# 從代碼中獲取的限制
MAX_DOCUMENT_CONTENT_LENGTH = 10000  # 單個文檔內容最多 10K 字符
MAX_DOCUMENT_TITLE_LENGTH = 200  # 文檔標題最多 200 字符
MAX_CONTEXT_CHARS = 15000  # 每次請求最多 15K 字符
MAX_DOCUMENTS = 5  # 最多處理 5 個來源
MAX_SINGLE_DOC_CHARS = 2000  # 單個文檔最多 2K 字符（發送給 API）
MAX_OUTPUT_TOKENS = 512  # 輸出最多 512 tokens

# 系統提示和問題部分大約佔用的字符數（估算）
SYSTEM_PROMPT_ESTIMATE = 500  # 系統提示約 500 字符
QUESTION_PROMPT_ESTIMATE = 200  # 問題部分約 200 字符
BUFFER = 100  # 緩衝區

print("=" * 60)
print("📊 文件上傳限制分析")
print("=" * 60)

print("\n【1. 數據庫存儲限制（可以上傳多少）】")
print(f"  ✅ 單個文檔標題：最多 {MAX_DOCUMENT_TITLE_LENGTH} 字符")
print(f"  ✅ 單個文檔內容：最多 {MAX_DOCUMENT_CONTENT_LENGTH:,} 字符（約 {MAX_DOCUMENT_CONTENT_LENGTH/1000:.1f}K）")
print(f"  ✅ 文檔數量：無限制（數據庫可以存儲任意數量的文檔）")
print(f"  ✅ 來源數量：無限制（可以有多個不同的來源）")

print("\n【2. 每次 API 請求的限制（實際使用時）】")
print(f"  ⚠️  最多處理來源數：{MAX_DOCUMENTS} 個來源")
print(f"  ⚠️  每次請求總字符數：最多 {MAX_CONTEXT_CHARS:,} 字符（約 {MAX_CONTEXT_CHARS/1000:.1f}K）")
print(f"  ⚠️  單個文檔發送長度：最多 {MAX_SINGLE_DOC_CHARS:,} 字符（約 {MAX_SINGLE_DOC_CHARS/1000:.1f}K）")
print(f"     （即使數據庫中存儲了 10K 字符，也只會發送前 2K 字符）")

# 計算實際可用於資料的字符數
available_for_data = MAX_CONTEXT_CHARS - SYSTEM_PROMPT_ESTIMATE - QUESTION_PROMPT_ESTIMATE - BUFFER
print(f"\n  📝 實際可用於資料的字符數：約 {available_for_data:,} 字符")

# 計算最佳情況（每個文檔 2K 字符）
best_case_docs = available_for_data // (MAX_SINGLE_DOC_CHARS + 100)  # +100 是格式字符
print(f"\n  💡 最佳情況（每個文檔 2K 字符）：")
print(f"     - 最多可以同時使用約 {best_case_docs} 個文檔")
print(f"     - 但受來源數限制，最多只能有 {MAX_DOCUMENTS} 個來源")

# 計算最差情況（每個文檔很小）
worst_case_docs = available_for_data // 300  # 假設每個文檔+格式約 300 字符
print(f"\n  💡 最差情況（每個文檔很小，約 200 字符）：")
print(f"     - 最多可以同時使用約 {worst_case_docs} 個文檔")
print(f"     - 但受來源數限制，最多只能有 {MAX_DOCUMENTS} 個來源")

print("\n【3. 配額限制】")
print(f"  ⏰ 每天請求次數：20 次")
print(f"  ⏰ 每分鐘請求次數：10 次")
print(f"  ⏰ 每分鐘 Token 限制：250K tokens（輸入+輸出）")

print("\n【4. 建議】")
print(f"  📌 可以上傳的文件數量：")
print(f"     - 數據庫中可以存儲任意數量的文檔（無限制）")
print(f"     - 建議每個來源的文檔內容控制在 {MAX_SINGLE_DOC_CHARS:,} 字符以內")
print(f"     - 建議總來源數控制在合理範圍內（雖然無限制，但每次只會使用前 {MAX_DOCUMENTS} 個相關來源）")
print(f"\n  📌 實際使用時：")
print(f"     - 系統會根據問題自動篩選最相關的 {MAX_DOCUMENTS} 個來源")
print(f"     - 每個來源的文檔會被截斷到 {MAX_SINGLE_DOC_CHARS:,} 字符")
print(f"     - 總字符數不超過 {MAX_CONTEXT_CHARS:,} 字符")
print(f"\n  📌 最佳實踐：")
print(f"     - 將長文檔拆分為多個較小的文檔（每個約 1.5K-2K 字符）")
print(f"     - 使用清晰的來源名稱，方便系統篩選")
print(f"     - 每個來源的文檔數量建議控制在 10-20 個以內")

print("\n" + "=" * 60)
print("✅ 總結：可以上傳很多文件，但每次只會使用最相關的 5 個來源")
print("=" * 60)

