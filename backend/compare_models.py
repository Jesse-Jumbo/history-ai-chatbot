#!/usr/bin/env python3
"""比較 Gemini 和 GPT 的上傳限制"""
import os

# 當前 Gemini 2.5 Flash-Lite 的限制
GEMINI_DAILY_REQUESTS = 20
GEMINI_RPM = 10  # 每分鐘請求數
GEMINI_TPM = 250000  # 每分鐘 tokens（輸入+輸出）
GEMINI_MAX_CONTEXT = 15000  # 每次請求最多 15K 字符（約 7.5K-15K tokens）
GEMINI_MAX_OUTPUT = 512  # 輸出最多 512 tokens

# GPT-5 的限制（假設，需要確認實際值）
GPT5_CONTEXT = 250000  # 25萬 tokens 上下文
# GPT-5mini 的限制（假設，需要確認實際值）
GPT5MINI_CONTEXT = 2500000  # 250萬 tokens 上下文

print("=" * 70)
print("📊 模型上傳限制比較分析")
print("=" * 70)

print("\n【當前使用：Gemini 2.5 Flash-Lite】")
print(f"  ✅ 每天請求次數：{GEMINI_DAILY_REQUESTS} 次")
print(f"  ✅ 每分鐘請求次數：{GEMINI_RPM} 次")
print(f"  ✅ 每分鐘 Token 限制：{GEMINI_TPM:,} tokens（輸入+輸出）")
print(f"  ✅ 每次請求上下文：最多 {GEMINI_MAX_CONTEXT:,} 字符（約 7.5K-15K tokens）")
print(f"  ✅ 每次請求輸出：最多 {GEMINI_MAX_OUTPUT} tokens")
print(f"\n  📝 每天可處理的總 Token 數：")
daily_input_tokens = GEMINI_DAILY_REQUESTS * (GEMINI_MAX_CONTEXT // 2)  # 假設平均 7.5K tokens/請求
daily_output_tokens = GEMINI_DAILY_REQUESTS * GEMINI_MAX_OUTPUT
daily_total_tokens = daily_input_tokens + daily_output_tokens
print(f"     - 輸入：約 {daily_input_tokens:,} tokens")
print(f"     - 輸出：約 {daily_output_tokens:,} tokens")
print(f"     - 總計：約 {daily_total_tokens:,} tokens")

print("\n【如果改用 GPT-5（25萬 Token 上下文）】")
print(f"  ⚠️  上下文窗口：{GPT5_CONTEXT:,} tokens")
print(f"  ⚠️  需要確認的配額限制：")
print(f"     - 每天請求次數：？")
print(f"     - 每分鐘請求次數：？")
print(f"     - 每分鐘 Token 限制：？")
print(f"     - 免費層級配額：？")
print(f"\n  💡 理論上每天可處理的數據量（假設與 Gemini 相同的請求限制）：")
if GPT5_CONTEXT > 0:
    # 假設每天 20 次請求，每次使用 80% 的上下文窗口
    gpt5_daily_input = 20 * (GPT5_CONTEXT * 0.8)
    gpt5_daily_output = 20 * 4000  # 假設每次輸出 4K tokens
    gpt5_daily_total = gpt5_daily_input + gpt5_daily_output
    print(f"     - 輸入：約 {gpt5_daily_input:,.0f} tokens（{gpt5_daily_input/1000:.1f}K）")
    print(f"     - 輸出：約 {gpt5_daily_output:,} tokens（{gpt5_daily_output/1000:.1f}K）")
    print(f"     - 總計：約 {gpt5_daily_total:,.0f} tokens（{gpt5_daily_total/1000:.1f}K）")
    print(f"\n  📈 相比 Gemini 的提升：")
    improvement = (gpt5_daily_input / daily_input_tokens) if daily_input_tokens > 0 else 0
    print(f"     - 每次請求可處理的數據量：約 {improvement:.1f}x")
    print(f"     - 每天可處理的總數據量：約 {gpt5_daily_total/daily_total_tokens:.1f}x")

print("\n【如果改用 GPT-5mini（250萬 Token 上下文）】")
print(f"  ⚠️  上下文窗口：{GPT5MINI_CONTEXT:,} tokens（{GPT5MINI_CONTEXT/1000:.0f}K）")
print(f"  ⚠️  需要確認的配額限制：")
print(f"     - 每天請求次數：？")
print(f"     - 每分鐘請求次數：？")
print(f"     - 每分鐘 Token 限制：？")
print(f"     - 免費層級配額：？")
print(f"\n  💡 理論上每天可處理的數據量（假設與 Gemini 相同的請求限制）：")
if GPT5MINI_CONTEXT > 0:
    # 假設每天 20 次請求，每次使用 80% 的上下文窗口
    gpt5mini_daily_input = 20 * (GPT5MINI_CONTEXT * 0.8)
    gpt5mini_daily_output = 20 * 4000  # 假設每次輸出 4K tokens
    gpt5mini_daily_total = gpt5mini_daily_input + gpt5mini_daily_output
    print(f"     - 輸入：約 {gpt5mini_daily_input:,.0f} tokens（{gpt5mini_daily_input/1000000:.1f}M）")
    print(f"     - 輸出：約 {gpt5mini_daily_output:,} tokens（{gpt5mini_daily_output/1000:.1f}K）")
    print(f"     - 總計：約 {gpt5mini_daily_total:,.0f} tokens（{gpt5mini_daily_total/1000000:.1f}M）")
    print(f"\n  📈 相比 Gemini 的提升：")
    improvement = (gpt5mini_daily_input / daily_input_tokens) if daily_input_tokens > 0 else 0
    print(f"     - 每次請求可處理的數據量：約 {improvement:.1f}x")
    print(f"     - 每天可處理的總數據量：約 {gpt5mini_daily_total/daily_total_tokens:.1f}x")

print("\n【重要注意事項】")
print("  ⚠️  實際配額限制取決於：")
print("     1. OpenAI 的免費層級配額政策")
print("     2. 每分鐘請求數限制（RPM）")
print("     3. 每分鐘 Token 限制（TPM）")
print("     4. 每天請求數限制（RPD）")
print("     5. 是否有免費層級，或需要付費")
print("\n  💡 建議：")
print("     - 查詢 OpenAI 官方文檔確認實際配額")
print("     - 確認是否有免費層級，或需要付費使用")
print("     - 考慮成本效益（GPT-5 可能比 GPT-5mini 貴）")
print("     - 根據實際需求選擇合適的模型")

print("\n" + "=" * 70)
print("📌 總結：GPT-5 和 GPT-5mini 的上下文窗口更大，但需要確認實際配額限制")
print("=" * 70)

