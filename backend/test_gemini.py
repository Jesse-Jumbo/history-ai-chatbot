#!/usr/bin/env python3
"""測試 Gemini API 是否可用"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 加载环境变量
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

if not GEMINI_API_KEY:
    print("❌ 錯誤：未設定 GEMINI_API_KEY 環境變數")
    print("請在 backend/.env 檔案中設定：GEMINI_API_KEY=your_api_key")
    exit(1)

print(f"✅ GEMINI_API_KEY 已設定")
print(f"📝 使用模型：{GEMINI_MODEL}")
print("\n正在測試 Gemini API...")

try:
    # 配置 Gemini API
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 創建模型
    model = genai.GenerativeModel(GEMINI_MODEL)
    
    # 測試簡單問題
    test_question = "你好，請用繁體中文回答：1+1等於多少？"
    print(f"\n測試問題：{test_question}")
    
    response = model.generate_content(
        test_question,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=100,
        )
    )
    
    print(f"\n✅ API 測試成功！")
    print(f"回答：{response.text}")
    print("\n🎉 Gemini API 可以正常使用！")
    
except Exception as e:
    error_msg = str(e)
    print(f"\n❌ API 測試失敗：{error_msg}")
    
    if "API_KEY" in error_msg or "api key" in error_msg.lower():
        print("💡 提示：請檢查 API Key 是否正確")
    elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower() or "429" in error_msg.lower():
        print("💡 提示：API 配額已用完或達到速率限制，請稍後再試")
    elif "model" in error_msg.lower() or "not found" in error_msg.lower():
        print(f"💡 提示：模型 {GEMINI_MODEL} 可能不存在，請檢查模型名稱")
    else:
        print(f"💡 提示：請檢查錯誤訊息並確認 API 設定正確")
    
    exit(1)

