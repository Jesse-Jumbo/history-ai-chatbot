from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
import uvicorn
import csv
import io
import os
import sys
import base64
from pathlib import Path
import httpx
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from database import (
    get_answer_from_db,
    add_qa_pair,
    add_document,
    get_all_documents,
    get_all_documents_with_content,
    batch_add_documents_from_csv,
    get_bot_config,
    update_bot_config,
    init_db,
    get_elderly_documents_with_content,
)
from ai_service import generate_answer_with_ai

# 導入 TTS 模組（從根目錄）
ROOT_DIR = Path(__file__).resolve().parent.parent
TTS_MODULE_PATH = ROOT_DIR / "tts_google.py"
if TTS_MODULE_PATH.exists():
    sys.path.insert(0, str(ROOT_DIR))
    try:
        from tts_google import tts_text_to_wav
    except ImportError as e:
        print(f"警告：無法導入 tts_google 模組：{e}")
        tts_text_to_wav = None
else:
    tts_text_to_wav = None
    print(f"警告：找不到 tts_google.py 在 {TTS_MODULE_PATH}")

# SAGE API 配置（如果 SAGE 在遠端機器）
SAGE_API_URL = os.getenv("SAGE_API_URL", "http://localhost:8001")  # SAGE 預設在 8001 端口

# 啟動和關閉事件處理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時
    init_db()
    
    # 自動導入訪談資料
    print("\n" + "=" * 60)
    print("  檢查並導入訪談資料...")
    print("=" * 60)
    try:
        # 檢查導入腳本是否存在
        import_script = Path(__file__).resolve().parent / "import_elderly_interviews.py"
        transcripts_dir = Path(__file__).resolve().parent / "訪談逐字稿"
        
        if import_script.exists() and transcripts_dir.exists():
            # 動態導入並執行
            import importlib.util
            spec = importlib.util.spec_from_file_location("import_elderly_interviews", import_script)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'import_elderly_interviews'):
                    module.import_elderly_interviews()
                    print("  ✅ 訪談資料檢查完成")
        else:
            if not transcripts_dir.exists():
                print(f"  ⚠️  訪談資料夾不存在: {transcripts_dir}")
            else:
                print(f"  ⚠️  導入腳本不存在: {import_script}")
    except Exception as e:
        print(f"  ⚠️  導入訪談資料時發生錯誤: {str(e)}")
        print("     可以手動執行: python import_elderly_interviews.py")
    print("=" * 60)
    
    # 檢查 SAGE API 連接
    print("\n" + "=" * 60)
    print("  檢查 SAGE API 連接...")
    print("=" * 60)
    print(f"  SAGE API URL: {SAGE_API_URL}")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SAGE_API_URL}/status")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ SAGE API 連接成功")
                print(f"     狀態: {data.get('status', 'unknown')}")
                print(f"     GPU: {'可用' if data.get('gpu_available') else '不可用'}")
            else:
                print(f"  ⚠️  SAGE API 響應異常 (狀態碼: {response.status_code})")
    except httpx.ConnectError:
        print(f"  ❌ 無法連接到 SAGE API ({SAGE_API_URL})")
        print(f"     請確認：")
        print(f"     1. SAGE API 服務是否正在運行")
        print(f"     2. SAGE_API_URL 配置是否正確")
        print(f"     3. 如果 SAGE 在遠端，確認網路連接")
        print(f"     提示：執行 'python test_sage_connection.py' 進行詳細診斷")
    except Exception as e:
        print(f"  ⚠️  檢查 SAGE API 時發生錯誤: {str(e)}")
    print("=" * 60 + "\n")
    
    yield
    
    # 關閉時（如果需要清理資源）

app = FastAPI(title="歷史系 AI 對話機器人", lifespan=lifespan)


# CORS 設定（允許跨域訪問）
# 從環境變數讀取允許的來源，如果沒有則允許所有來源（開發環境）
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
if ALLOWED_ORIGINS == ["*"]:
    # 開發環境：允許所有來源
    allow_origins = ["*"]
else:
    # 生產環境：只允許指定的來源
    allow_origins = [origin.strip() for origin in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str
    use_ai: bool = True  # 是否使用 AI 增強回答

class QuestionResponse(BaseModel):
    answer: str
    source: str  # "database" 或 "ai" 或 "documents+ai" 或 "none"
    documents_used: Optional[List[dict]] = None  # 使用的文檔（包含來源 ID）
    source_ids: Optional[List[str]] = None  # 來源 ID 列表
    source_details: Optional[List[dict]] = None  # 來源詳細信息：{"source": "來源ID", "doc_titles": ["資料1", "資料2"]}

class DocumentRequest(BaseModel):
    title: str
    content: str
    category: str = "general"
    source: str = ""

class DocumentResponse(BaseModel):
    id: int
    title: str
    category: str
    source: str
    created_at: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "歷史系 AI 對話機器人 API"}

@app.get("/api/bot-config")
async def get_bot_config_endpoint():
    """獲取機器人配置（角色/身份）"""
    try:
        config = get_bot_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 數據上限設定
MAX_ROLE_NAME_LENGTH = 50  # 角色名稱最多 50 字符
MAX_ROLE_DESCRIPTION_LENGTH = 500  # 角色描述最多 500 字符
MAX_DOCUMENT_CONTENT_LENGTH = 10000  # 單個文檔內容最多 10K 字符
MAX_DOCUMENT_TITLE_LENGTH = 200  # 文檔標題最多 200 字符

class BotConfigRequest(BaseModel):
    role_name: str
    role_description: Optional[str] = None

@app.put("/api/bot-config")
async def update_bot_config_endpoint(request: BotConfigRequest):
    """更新機器人配置（角色/身份）"""
    try:
        # 驗證數據上限
        if len(request.role_name) > MAX_ROLE_NAME_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"角色名稱過長，最多 {MAX_ROLE_NAME_LENGTH} 字符（目前：{len(request.role_name)} 字符）"
            )
        
        if request.role_description and len(request.role_description) > MAX_ROLE_DESCRIPTION_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"角色描述過長，最多 {MAX_ROLE_DESCRIPTION_LENGTH} 字符（目前：{len(request.role_description)} 字符）"
            )
        
        update_bot_config(
            role_name=request.role_name.strip(),
            role_description=request.role_description.strip() if request.role_description else None
        )
        return {
            "message": "機器人配置已更新，對話歷史已清空", 
            "config": get_bot_config(),
            "clear_chat": True  # 標記需要清空對話
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============== TTS API ==============

class TTSRequest(BaseModel):
    text: str
    lang: str = "zh-TW"
    voice_name: Optional[str] = None
    rate: float = 0.9  # 老人聲音稍慢
    pitch: float = -2.0  # 老人聲音較低

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """文字轉語音（使用 Google TTS）"""
    if not tts_text_to_wav:
        raise HTTPException(status_code=503, detail="TTS 服務未配置，請確認 tts_google.py 存在且 GOOGLE_APPLICATION_CREDENTIALS 已設定")
    
    try:
        # 生成臨時 WAV 檔案
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_filename = f"tts_{timestamp}.wav"
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(exist_ok=True)
        
        # 調用 TTS
        wav_path = tts_text_to_wav(
            text=request.text,
            out=output_filename,
            out_dir=output_dir,
            lang=request.lang,
            voice_name=request.voice_name,
            rate=request.rate,
            pitch=request.pitch,
            sr=24000
        )
        
        # 返回音訊檔案
        return FileResponse(
            str(wav_path),
            media_type="audio/wav",
            filename=output_filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 生成失敗：{str(e)}")

# ============== SAGE API 代理 ==============

class AgePhotoRequest(BaseModel):
    image_base64: str
    target_age: int = 75
    mock: bool = False  # 預設使用真實模型

@app.post("/api/age-photo")
async def age_photo_proxy(request: AgePhotoRequest):
    """代理 SAGE API：變老照片"""
    try:
        # 檢查圖片大小（避免過大）
        if len(request.image_base64) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="圖片過大，請使用較小的圖片")
        
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 分鐘超時（變老處理需要時間）
            try:
                # 記錄請求資訊（調試用）
                print(f"[DEBUG] 發送請求到 SAGE API: {SAGE_API_URL}/age/photo")
                print(f"[DEBUG] 圖片大小: {len(request.image_base64)} 字符")
                print(f"[DEBUG] 目標年齡: {request.target_age}, Mock: {request.mock}")
                
                response = await client.post(
                    f"{SAGE_API_URL}/age/photo",
                    json={
                        "image_base64": request.image_base64,
                        "target_age": request.target_age,
                        "mock": request.mock
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=300.0
                )
                
                print(f"[DEBUG] SAGE API 響應狀態碼: {response.status_code}")
                response.raise_for_status()
                
                result = response.json()
                print(f"[DEBUG] SAGE API 返回成功: {result.get('success', False)}")
                return result
            except httpx.ConnectError as e:
                print(f"[ERROR] 連接錯誤: {str(e)}")
                print(f"[ERROR] SAGE API URL: {SAGE_API_URL}")
                error_msg = (
                    f"無法連接到 SAGE API ({SAGE_API_URL})。"
                    f"請確認：\n"
                    f"1. SAGE API 服務是否正在運行\n"
                    f"2. SAGE_API_URL 配置是否正確（當前：{SAGE_API_URL})\n"
                    f"3. 網路連接是否正常\n"
                    f"4. 防火牆是否允許連接\n"
                    f"錯誤詳情：{str(e)}"
                )
                raise HTTPException(status_code=503, detail=error_msg)
            except httpx.TimeoutException as e:
                print(f"[ERROR] 請求超時: {str(e)}")
                raise HTTPException(status_code=504, detail="SAGE API 請求超時，變老處理可能需要較長時間（最多 5 分鐘）")
            except httpx.HTTPStatusError as e:
                print(f"[ERROR] HTTP 錯誤: {e.response.status_code}")
                print(f"[ERROR] 響應內容: {e.response.text[:500]}")
                error_detail = f"SAGE API 返回錯誤 {e.response.status_code}"
                try:
                    error_json = e.response.json()
                    if "detail" in error_json:
                        error_detail += f": {error_json['detail']}"
                    else:
                        error_detail += f": {error_json}"
                except:
                    error_detail += f": {e.response.text[:200]}"
                raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            f"處理請求時發生錯誤：{str(e)}\n"
            f"SAGE API URL: {SAGE_API_URL}\n"
            f"請檢查後端日誌以獲取更多資訊"
        )
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/capture-and-age")
async def capture_and_age_proxy(
    file: UploadFile = File(...),
    target_age: int = Form(75),
    mock: bool = Form(False)
):
    """代理 SAGE API：上傳照片並變老"""
    try:
        # 讀取上傳的檔案
        contents = await file.read()
        image_base64 = base64.b64encode(contents).decode('utf-8')
        
        # 調用變老 API
        request = AgePhotoRequest(
            image_base64=image_base64,
            target_age=target_age,
            mock=mock
        )
        return await age_photo_proxy(request)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"處理失敗：{str(e)}")

@app.get("/api/sage-status")
async def sage_status():
    """檢查 SAGE API 狀態"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{SAGE_API_URL}/status")
                response.raise_for_status()
                status_data = response.json()
                status_data["connected"] = True
                status_data["sage_api_url"] = SAGE_API_URL
                return status_data
            except httpx.ConnectError as e:
                return {
                    "status": "offline",
                    "connected": False,
                    "error": f"無法連接到 SAGE API: {str(e)}",
                    "sage_api_url": SAGE_API_URL,
                    "suggestion": "請確認 SAGE API 服務是否正在運行，以及 SAGE_API_URL 配置是否正確"
                }
            except httpx.TimeoutException:
                return {
                    "status": "timeout",
                    "connected": False,
                    "error": "連接超時",
                    "sage_api_url": SAGE_API_URL
                }
            except httpx.HTTPStatusError as e:
                return {
                    "status": "error",
                    "connected": False,
                    "error": f"SAGE API 返回錯誤 {e.response.status_code}: {e.response.text[:200]}",
                    "sage_api_url": SAGE_API_URL
                }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
            "sage_api_url": SAGE_API_URL
        }

@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    處理使用者問題（使用 Gemini API）
    1. 獲取所有文檔資料
    2. 使用 Gemini API 基於所有資料生成答案
    """
    try:
        # 1. 獲取機器人配置（角色/身份）
        bot_config = get_bot_config()
        
        # 2. 優先獲取「老人訪談」文檔；若沒有，再回退到僅用模型知識
        elderly_documents = get_elderly_documents_with_content()
        if elderly_documents:
            documents_for_ai = elderly_documents
        else:
            # 如果還有其他一般文檔，之後如有需要可以在這裡接回
            documents_for_ai = None
        
        # 3. 使用 Gemini API 生成答案（即使沒有資料也可以使用 Gemini 基礎能力）
        if request.use_ai:
            try:
                ai_answer = await generate_answer_with_ai(
                    question=request.question,
                    # 如果有老人訪談資料就傳入，沒有就傳 None（只用模型知識）
                    documents=documents_for_ai if documents_for_ai else None,
                    role_name=bot_config.get("role_name", "成功大學歷史系的對話機器人"),
                    role_description=bot_config.get("role_description")
                )
                
                # 收集所有來源信息（如果有資料）
                source_ids = None
                source_details = None
                if documents_for_ai:
                    source_ids = [doc.get("source", "") for doc in documents_for_ai if doc.get("source")]
                    source_details = [
                        {
                            "source": doc.get("source", ""),
                            "doc_titles": doc.get("doc_titles", [])
                        }
                        for doc in documents_for_ai
                        if doc.get("source")
                    ]
                
                return QuestionResponse(
                    answer=ai_answer,
                    source="ai" if not documents_for_ai else "documents+ai",
                    documents_used=documents_for_ai if documents_for_ai else None,
                    source_ids=source_ids,
                    source_details=source_details
                )
            except Exception as e:
                # AI 失败时，返回错误信息
                raise HTTPException(status_code=500, detail=f"AI 服務錯誤：{str(e)}")
        else:
            # 如果不使用 AI，返回第一個文檔的內容
            if documents_for_ai:
                source_ids = [doc.get("source", "") for doc in documents_for_ai if doc.get("source")]
                source_details = [
                    {
                        "source": doc.get("source", ""),
                        "doc_titles": doc.get("doc_titles", [])
                    }
                    for doc in documents_for_ai
                    if doc.get("source")
                ]
                return QuestionResponse(
                    answer=documents_for_ai[0].get("content", ""),
                    source="documents",
                    documents_used=documents_for_ai,
                    source_ids=source_ids,
                    source_details=source_details if source_details else None
                )
            
            return QuestionResponse(
                answer="抱歉，我目前沒有這個問題的答案。",
                source="none",
                source_ids=None
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/add-qa")
async def add_qa(request: QuestionRequest):
    """新增問答對到資料庫（管理用）"""
    try:
        # 獲取機器人配置
        bot_config = get_bot_config()
        
        # 獲取所有文檔並使用 AI 生成答案
        documents = get_elderly_documents_with_content() or None
        answer = await generate_answer_with_ai(
            request.question, 
            documents=documents if documents else None,
            role_name=bot_config.get("role_name", "成功大學歷史系的對話機器人"),
            role_description=bot_config.get("role_description")
        )
        add_qa_pair(request.question, answer)
        return {"message": "問答對已新增"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents", response_model=dict)
async def create_document(doc: DocumentRequest):
    """新增歷史資料文檔"""
    try:
        # 驗證數據上限
        if len(doc.title) > MAX_DOCUMENT_TITLE_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"文檔標題過長，最多 {MAX_DOCUMENT_TITLE_LENGTH} 字符（目前：{len(doc.title)} 字符）"
            )
        if len(doc.content) > MAX_DOCUMENT_CONTENT_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"文檔內容過長，最多 {MAX_DOCUMENT_CONTENT_LENGTH} 字符（目前：{len(doc.content)} 字符）"
            )
        
        doc_id = add_document(
            title=doc.title.strip(),
            content=doc.content.strip(),
            category=doc.category,
            source=doc.source.strip()
        )
        return {"message": "文檔已新增", "id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: int):
    """獲取單個文檔的詳細內容"""
    try:
        from database import get_document_by_id
        doc = get_document_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文檔不存在")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents", response_model=List[DocumentResponse])
async def list_documents():
    """獲取所有文檔列表"""
    try:
        docs = get_all_documents()
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/documents/clear")
async def clear_all_documents():
    """清空所有文檔和問答對（刪除所有資料）"""
    try:
        from database import SessionLocal, Document, QAPair
        db = SessionLocal()
        try:
            doc_count = db.query(Document).count()
            qa_count = db.query(QAPair).count()
            # 刪除所有文檔
            db.query(Document).delete(synchronize_session=False)
            # 刪除所有問答對
            db.query(QAPair).delete(synchronize_session=False)
            db.commit()
            return {
                "message": f"已清空所有資料，共刪除 {doc_count} 筆文檔和 {qa_count} 筆問答對",
                "doc_count": doc_count,
                "qa_count": qa_count
            }
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失敗：{str(e)}")

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: int):
    """刪除指定文檔"""
    try:
        from database import SessionLocal, Document
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="文檔不存在")
            db.delete(doc)
            db.commit()
            return {"message": "文檔已刪除", "id": doc_id}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗：{str(e)}")

@app.delete("/api/documents/source/{source_id}")
async def delete_documents_by_source(source_id: str):
    """根據來源 ID 批量刪除文檔"""
    try:
        from database import SessionLocal, Document
        db = SessionLocal()
        try:
            docs = db.query(Document).filter(Document.source == source_id).all()
            if not docs:
                raise HTTPException(status_code=404, detail=f"找不到來源 '{source_id}' 的文檔")
            count = len(docs)
            for doc in docs:
                db.delete(doc)
            db.commit()
            return {"message": f"已刪除 {count} 筆來源為 '{source_id}' 的文檔", "count": count}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除失敗：{str(e)}")


@app.post("/api/documents/batch")
async def batch_import_documents(documents: List[DocumentRequest]):
    """批量導入文檔"""
    try:
        imported = []
        for doc in documents:
            doc_id = add_document(
                title=doc.title,
                content=doc.content,
                category=doc.category,
                source=doc.source
            )
            imported.append(doc_id)
        return {"message": f"成功導入 {len(imported)} 個文檔", "ids": imported}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """上傳 CSV 文件並批量導入資料
    
    CSV 格式要求：
    - 必須有 'id' 和 'text' 兩個欄位
    - id: 資料名稱（每行的 id 字段會作為該筆資料的標題）
    - text: 內容
    - 整個 CSV 文件會作為一個來源，來源名稱是文件名（不含擴展名）
    """
    try:
        # 獲取文件名（不含擴展名）作為來源 ID
        filename = file.filename or "unknown"
        # 移除 .csv 擴展名
        source_id = filename.replace('.csv', '').replace('.CSV', '')
        
        # 讀取文件內容
        contents = await file.read()
        text = contents.decode('utf-8-sig')  # 處理 BOM
        
        # 解析 CSV
        csv_reader = csv.DictReader(io.StringIO(text))
        rows = []
        for idx, row in enumerate(csv_reader, 1):
            # 檢查必要欄位
            if 'id' not in row or 'text' not in row:
                raise HTTPException(
                    status_code=400, 
                    detail="CSV 文件必須包含 'id' 和 'text' 兩個欄位"
                )
            # id 作為資料名稱，source 使用文件名
            doc_id = row['id'].strip()
            if not doc_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV 文件第 {idx} 行的 'id' 欄位不能為空"
                )
            
            text_content = row['text'].strip()
            
            # 驗證數據上限
            if len(doc_id) > MAX_DOCUMENT_TITLE_LENGTH:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV 文件第 {idx} 行的標題過長，最多 {MAX_DOCUMENT_TITLE_LENGTH} 字符（目前：{len(doc_id)} 字符）"
                )
            if len(text_content) > MAX_DOCUMENT_CONTENT_LENGTH:
                raise HTTPException(
                    status_code=400,
                    detail=f"CSV 文件第 {idx} 行的內容過長，最多 {MAX_DOCUMENT_CONTENT_LENGTH} 字符（目前：{len(text_content)} 字符）"
                )
            
            rows.append({
                "id": doc_id,  # CSV 中的 id 作為資料名稱（title）
                "source": source_id,  # 文件名作為來源 ID
                "text": text_content
            })
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV 文件為空或格式錯誤")
        
        # 批量導入（所有資料都屬於同一個來源）
        # 不再生成 embedding，直接導入
        count = batch_add_documents_from_csv(rows, generate_embeddings=False)
        
        return {
            "message": f"成功從 CSV 文件「{source_id}」導入 {count} 筆資料",
            "count": count,
            "source": source_id,
            "source_count": 1  # 只有一個來源（文件名）
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"導入失敗：{str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

