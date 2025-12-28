import os
from typing import Optional, List, Dict
import google.generativeai as genai

# Gemini API 配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# 配置 Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def build_system_prompt(role_name: str, role_description: str = None) -> str:
    """
    根據角色設定構建 System Prompt

    對應產品設定：
    - 你是「使用者變老後、住在療養院的自己」
    - 優先根據「老人訪談逐字稿」回答，沒有再用自己的一般知識
    """
    base_role = (
        "你是使用者本人在未來變老後的樣子，現在住在一間療養院。"
        "你以第一人稱『我』來說話，就像在跟年輕時的自己聊天。"
    )

    if role_description:
        role_part = f"{base_role} 你的名稱或身份設定是：{role_name}。{role_description}"
    else:
        role_part = f"{base_role} 你的名稱或身份設定是：{role_name}。"

    prompt = f"""{role_part}
請「務必」使用繁體中文回答，語氣要像真實的老人聊天，而不是教科書式的講解。

**資料來源優先順序**
- 如果有系統提供的「老人訪談逐字稿」內容，請優先根據這些內容回答，當成是你自己過去在訪談中說過的話。
- 如果逐字稿中沒有相關內容，再使用你自己的知識或一般常識來補充回答。
- 如果你不確定或沒有足夠資訊，請老實說你不確定，不要亂編。

**回答規範**
- 一律使用繁體中文。
- 用第一人稱「我」說話，對話對象是「你」。
- 風格像聊天，可以帶一點回憶、感想，但不要一次講太長。
- 儘量控制在 2–3 句話內，如果需要講很多，再先問使用者要不要聽更詳細的版本。
- 回答可以使用簡單的 Markdown（例如粗體、列表）讓版面更清楚，但不要過度格式化。
"""
    return prompt

# Gemini 2.5 Flash-Lite 免費額度限制
# 限制：每天 20 次請求，每分鐘 10 次請求
# Token 限制：每分鐘 250K tokens（輸入+輸出）
# 為了安全，限制每次請求最多 15K 字符（約 7.5K-15K tokens，保守估計）
# 輸出限制：最多 512 tokens（約 1K 字符）
MAX_CONTEXT_CHARS = 15000  # 15K 字符（約 7.5K-15K tokens）
MAX_DOCUMENTS = 5  # 最多處理 5 個來源
MAX_SINGLE_DOC_CHARS = 2000  # 單個文檔最多 2K 字符
MAX_OUTPUT_TOKENS = 512  # 最多輸出 512 tokens

def estimate_tokens(text: str) -> int:
    """估算 token 數量（中文約 1-2 字符 = 1 token）"""
    return len(text) // 1.5

def filter_relevant_documents(question: str, documents: List[Dict], max_docs: int = MAX_DOCUMENTS) -> List[Dict]:
    """
    根據問題篩選相關文檔（簡單關鍵詞匹配）
    
    Args:
        question: 使用者問題
        documents: 所有文檔列表
        max_docs: 最多返回的文檔數量
    
    Returns:
        篩選後的相關文檔列表
    """
    if not documents or not question:
        return documents[:max_docs] if documents else []
    
    import re
    
    # 提取問題中的關鍵詞（中文詞，2-4字）
    # 排除常見停用詞
    stop_words = {'什麼', '如何', '怎樣', '為何', '為什麼', '何時', '哪裡', '哪個', '多少', 
                  '的', '了', '是', '在', '有', '會', '要', '可以', '能夠', '這個', '那個'}
    
    # 提取中文詞（2-4字）
    keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
    keywords = [kw for kw in keywords if kw not in stop_words]
    
    if not keywords:
        # 如果沒有關鍵詞，返回前 N 個文檔
        return documents[:max_docs]
    
    # 為每個文檔計算相關度分數
    scored_docs = []
    for doc in documents:
        title = doc.get('title', '')
        content = doc.get('content', '')
        text = f"{title} {content}"
        
        # 計算關鍵詞匹配分數
        score = 0
        for keyword in keywords[:5]:  # 只使用前 5 個關鍵詞
            # 標題匹配權重更高
            if keyword in title:
                score += 3
            # 內容匹配
            if keyword in content:
                score += 1
        
        scored_docs.append((score, doc))
    
    # 按分數排序（降序）
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    # 如果最高分為 0，說明沒有匹配，返回前 N 個
    if scored_docs[0][0] == 0:
        return documents[:max_docs]
    
    # 返回分數最高的文檔（至少包含有匹配的文檔）
    result = [doc for score, doc in scored_docs if score > 0]
    
    # 如果匹配的文檔太少，補充一些高分文檔
    if len(result) < max_docs:
        remaining = max_docs - len(result)
        for score, doc in scored_docs:
            if doc not in result and remaining > 0:
                result.append(doc)
                remaining -= 1
    
    return result[:max_docs]

def truncate_documents(documents: List[Dict], max_chars: int = MAX_CONTEXT_CHARS) -> List[Dict]:
    """
    截斷文檔列表，確保總字符數不超過限制
    
    Args:
        documents: 文檔列表
        max_chars: 最大字符數限制
    
    Returns:
        截斷後的文檔列表
    """
    if not documents:
        return []
    
    # 先限制文檔數量
    limited_docs = documents[:MAX_DOCUMENTS]
    
    total_chars = 0
    result = []
    
    for doc in limited_docs:
        source_id = doc.get('source', '未知來源')
        title = doc.get('title', '')
        content = doc.get('content', '')
        
        # 先截斷單個文檔的內容（如果太長）
        if len(content) > MAX_SINGLE_DOC_CHARS:
            content = content[:MAX_SINGLE_DOC_CHARS] + "...（內容已截斷）"
        
        # 計算這個文檔需要的字符數
        doc_text = f"\n【來源：{source_id}】\n標題：{title}\n內容：{content}"
        doc_chars = len(doc_text)
        
        # 如果加上這個文檔會超過限制，截斷內容或停止
        if total_chars + doc_chars > max_chars:
            remaining_chars = max_chars - total_chars - len(f"\n【來源：{source_id}】\n標題：{title}\n內容：")
            if remaining_chars > 200:  # 至少保留 200 字符
                truncated_content = content[:remaining_chars] + "...（內容已截斷）"
                result.append({
                    "source": source_id,
                    "title": title,
                    "content": truncated_content
                })
            # 無論如何都停止，因為已經達到限制
            break
        
        result.append({
            "source": source_id,
            "title": title,
            "content": content
        })
        total_chars += doc_chars
    
    return result

async def generate_answer_with_ai(
    question: str, 
    documents: Optional[List[Dict]] = None,
    role_name: str = "你是使用者本人在未來變老後的樣子，現在住在一間療養院。你以第一人稱『我』來說話，就像在跟年輕時的自己聊天。",
    role_description: str = None
) -> str:
    """
    使用 Gemini API 生成答案
    
    Args:
        question: 使用者問題
        documents: 相關文檔列表，格式：[{"source": "來源ID", "title": "標題", "content": "內容"}, ...]
    
    Returns:
        AI 生成的答案
    """
    if not GEMINI_API_KEY:
        return "錯誤：未設定 GEMINI_API_KEY 環境變數。請在 .env 檔案中設定您的 Gemini API Key。"
    
    try:
        # 構建上下文
        context_parts = []
        
        if documents:
            # 先根據問題篩選相關文檔（只選擇相關的，不發送全部）
            relevant_docs = filter_relevant_documents(question, documents, MAX_DOCUMENTS)
            
            # 再限制文檔大小
            limited_docs = truncate_documents(relevant_docs, MAX_CONTEXT_CHARS)
            
            if len(limited_docs) < len(documents):
                context_parts.append(f"=== 歷史資料庫內容（已限制為前 {len(limited_docs)} 個來源，共 {len(documents)} 個來源） ===")
            else:
                context_parts.append("=== 歷史資料庫內容 ===")
            
            for doc in limited_docs:
                source_id = doc.get('source', '未知來源')
                title = doc.get('title', '')
                content = doc.get('content', '')
                
                context_parts.append(f"\n【來源：{source_id}】")
                if title:
                    context_parts.append(f"標題：{title}")
                if content:
                    context_parts.append(f"內容：{content}")
        
        # 構建 System Prompt
        system_prompt = build_system_prompt(role_name, role_description)
        
        # 構建完整提示
        if context_parts:
            context_text = "\n".join(context_parts)
            
            # 檢查總長度，確保不超過限制
            user_prompt_base = f"\n\n=== 問題 ===\n{question}\n\n請根據以上資料回答問題。**務必確保回答的是問題中問到的人本人的信息，而不是其他人的信息。**如果資料中有相關內容，請在回答中明確指出來源（來源 ID）。如果資料中沒有相關內容，請使用你的知識庫來回答。"
            
            # 計算可用於資料的字符數
            system_prompt_len = len(system_prompt)
            user_prompt_base_len = len(user_prompt_base)
            available_chars = MAX_CONTEXT_CHARS - system_prompt_len - user_prompt_base_len - 100  # 保留100字符緩衝
            
            # 如果資料太長，截斷
            if len(context_text) > available_chars:
                context_text = context_text[:available_chars] + "\n\n（資料過多，已截斷部分內容）"
            
            prompt_text = f"{system_prompt}{user_prompt_base}\n\n{context_text}"
        else:
            # 沒有上傳資料，只使用模型知識
            system_prompt = build_system_prompt(role_name, role_description)
            prompt_text = f"{system_prompt}\n\n問題：{question}\n\n請回答這個問題。"
        
        # 調用 Gemini API（添加重試機制和更好的錯誤處理）
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        max_retries = 2  # 減少重試次數，避免過多請求
        retry_delay = 3  # 增加等待時間
        
        # 最後檢查：如果 prompt 還是太長，只保留系統提示和問題
        if len(prompt_text) > MAX_CONTEXT_CHARS:
            system_prompt = build_system_prompt(role_name, role_description)
            prompt_text = f"{system_prompt}\n\n問題：{question}\n\n請回答這個問題。"
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    prompt_text,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        max_output_tokens=MAX_OUTPUT_TOKENS,  # 使用設定的輸出長度限制
                    )
                )
                return response.text
            except Exception as retry_error:
                error_msg = str(retry_error).lower()
                # 如果是配額錯誤，等待後重試
                if ("quota" in error_msg or "rate limit" in error_msg or "429" in error_msg) and attempt < max_retries - 1:
                    import time
                    wait_time = retry_delay * (attempt + 1)  # 指數退避：3秒、6秒
                    time.sleep(wait_time)
                    continue
                else:
                    raise retry_error
    
    except Exception as e:
        error_msg = str(e)
        if "API_KEY" in error_msg or "api key" in error_msg.lower():
            return f"錯誤：Gemini API Key 無效或未設定。請檢查 .env 檔案中的 GEMINI_API_KEY。"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return "錯誤：已達到 API 使用配額或速率限制。請稍後再試。"
        else:
            return f"錯誤：無法生成答案。{error_msg}"
