import requests
import os
from typing import Optional, List, Dict

# Ollama API 端點（預設本地）
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

async def generate_answer_with_ai(question: str, context: Optional[str] = None, documents: Optional[List[Dict]] = None) -> str:
    """
    使用 Ollama 生成答案（RAG 模式）
    
    Args:
        question: 使用者問題
        context: 可選的資料庫上下文（問答對）
        documents: 可選的相關文檔列表
    
    Returns:
        AI 生成的答案
    """
    # 構建提示詞
    system_prompt = """你是一個專業的歷史系 AI 助手，專門回答歷史相關問題。
請「務必」使用繁體中文回答，回答要準確、詳細且易懂。

**重要：準確理解問題意圖**
- 如果問題問的是某個人的出生、死亡、事件等，你必須只回答該人本人的信息
- 如果資料中提到的是該人的親屬、子女、他人的信息，而不是該人本人的信息，請明確說明「資料中沒有找到該人本人的相關信息」
- 例如：如果問「張三何時出生」，資料中只有「張三的兒子李四於某日出生」，這不是答案，應該說找不到張三本人的出生信息

**智能判斷信息完整性**
- 如果提供的資料已經足夠完整回答問題，請直接回答，不需要等待更多資料
- 如果提供的資料不夠完整，但已經包含主要信息，也可以基於現有資料回答
- 只有在完全沒有相關信息時，才說「抱歉，我在資料庫中找不到相關內容，無法回答這個問題。」

如果提供的資料中有相關資訊，請優先使用資料中的內容來回答，並明確指出來源。
請確保所有回答都是繁體中文，不要使用簡體中文或英文。"""
    
    # 構建上下文
    context_parts = []
    
    if documents:
        context_parts.append("=== 相關歷史資料（請在回答中註明來源） ===")
        # 優化：智能選擇最相關的文檔，優先處理相似度高的
        # 如果文檔很多，優先使用前 20 個最相關的來源
        # AI 可以根據這些信息判斷是否已經足夠回答問題
        prioritized_docs = documents[:20]  # 優先使用前 20 個最相關的來源
        
        for i, doc in enumerate(prioritized_docs, 1):
            source_id = doc.get('source', '未知來源')
            doc_titles = doc.get('doc_titles', [])
            context_parts.append(f"\n【來源：{source_id}】")
            if doc_titles:
                # 如果資料很多，只顯示前 10 個
                display_titles = doc_titles[:10]
                if len(doc_titles) > 10:
                    context_parts.append(f"相關資料：{', '.join(display_titles)}（共 {len(doc_titles)} 筆）")
                else:
                    context_parts.append(f"相關資料：{', '.join(display_titles)}")
            # 使用full_content确保包含完整信息，但如果太长则截取最相关的部分
            full_content = doc.get('full_content', '')
            content = doc.get('content', '')
            
            # 优先使用full_content，确保包含完整信息
            # 但如果太长，智能提取最相关的部分
            if len(full_content) <= 4000:
                # 内容不太长，直接使用完整内容
                context_parts.append(f"內容：{full_content}")
            else:
                # 内容太长，智能提取最相关的部分
                import re
                # 从问题中提取关键词
                keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
                exclude_words = ['何時', '什麼', '時候', '日期', '年月', '年', '月', '日', '的', '了', '是', '在', '有', '會', '要', '可以', '能夠', '如何', '怎樣']
                keywords = [k for k in keywords if k not in exclude_words and len(k) >= 2]
                
                # 找到包含最多关键词的段落（优先使用）
                best_segments = []
                if keywords:
                    # 在full_content中滑动窗口，找到包含最多关键词的段落
                    window_size = 2000
                    step = 500
                    segments = []
                    
                    for start in range(0, min(len(full_content), 15000), step):
                        end = min(start + window_size, len(full_content))
                        window = full_content[start:end]
                        # 计算关键词匹配分数
                        score = sum(1 for kw in keywords[:5] if kw in window)
                        if score > 0:
                            segments.append((score, start, end, window))
                    
                    # 按分数排序，取前3个最相关的段落
                    segments.sort(reverse=True, key=lambda x: x[0])
                    best_segments = [seg[3] for seg in segments[:3]]
                
                # 如果找到了相关段落，使用它们
                if best_segments:
                    combined = "\n\n...\n\n".join(best_segments)
                    # 限制总长度
                    if len(combined) > 4000:
                        combined = combined[:4000] + "..."
                    context_parts.append(f"內容：{combined}")
                else:
                    # 如果没找到，使用提取的content
                    context_parts.append(f"內容：{content}")
    
    if context:
        context_parts.append("\n=== 資料庫問答 ===")
        context_parts.append(context)
    
    user_prompt = question
    if context_parts:
        context_text = "\n".join(context_parts)
        # 從問題中提取人名（如果有的話）
        import re
        name_parts = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
        exclude_words = ['出生', '報生', '誕生', '何時', '什麼', '時候', '日期', '年月', '年', '月', '日', '的', '了', '是', '在', '有', '會', '要', '可以', '能夠']
        person_name = [p for p in name_parts if p not in exclude_words and len(p) >= 2]
        
        person_context = ""
        if person_name:
            person_context = f"\n\n**特別注意**：問題問的是「{person_name[0]}」本人的信息。如果資料中提到的是「{person_name[0]}的親屬」、「{person_name[0]}的子女」、「{person_name[0]}的家人」或其他人的信息，而不是「{person_name[0]}」本人的信息，請明確說明「資料中沒有找到{person_name[0]}本人的相關信息」。"
        
        user_prompt = f"{context_text}{person_context}\n\n=== 問題 ===\n{question}\n\n請根據以上資料回答問題。**務必確保回答的是問題中問到的人本人的信息，而不是其他人的信息。**如果資料中有相關內容，請在回答中明確指出來源（來源 ID）。如果資料中沒有相關內容，請直接說「抱歉，我在資料庫中找不到相關內容，無法回答這個問題。」"
    
    # 調用 Ollama API
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"{system_prompt}\n\n問題：{user_prompt}\n\n回答：",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 250,  # 優化：進一步限制生成长度，提升速度
                    "num_ctx": 1536,  # 優化：減少上下文長度，提升處理速度
                    "top_k": 20,  # 優化：減少候選詞數量
                    "top_p": 0.9  # 優化：使用核採樣加速
                }
            },
            timeout=60  # 優化：減少超時時間，提升響應速度
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "抱歉，我無法生成答案。")
    
    except requests.exceptions.Timeout:
        # 超时情况：返回找到的文档内容摘要
        if documents:
            sources = [doc.get('source', '未知') for doc in documents]
            content_summary = "\n\n".join([
                f"【來源：{doc.get('source', '未知')}】\n{doc.get('content', '')[:200]}..."
                for doc in documents[:2]
            ])
            return f"根據資料庫中的資料：\n\n{content_summary}\n\n（註：AI 處理時間較長，以上為資料庫中的相關內容摘要。來源：{', '.join(sources)}）"
        return "AI 服務響應超時。請確認 Ollama 已啟動，或嘗試使用較小的模型（如 qwen2.5:3b）。"
    
    except requests.exceptions.RequestException as e:
        # 如果 Ollama 未運行或其他錯誤，返回找到的文档内容
        if documents:
            sources = [doc.get('source', '未知') for doc in documents]
            content_summary = "\n\n".join([
                f"【來源：{doc.get('source', '未知')}】\n{doc.get('content', '')[:300]}..."
                for doc in documents[:2]
            ])
            return f"根據資料庫中的資料：\n\n{content_summary}\n\n（註：AI 服務暫時無法使用，以上為資料庫中的相關內容。來源：{', '.join(sources)}）"
        return f"AI 服務暫時無法使用。請確認 Ollama 已啟動並安裝了模型 {OLLAMA_MODEL}。錯誤：{str(e)}"

