"""
SAGE API Server - FastAPI Remote Access
提供遠端 HTTP API 存取 SAGE 功能
"""
import sys
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from contextlib import asynccontextmanager

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
import numpy as np

from config.settings import (
    CAPTURED_DIR, AGED_DIR,
    AUTO_MOCK, MOCK_MODE, DEFAULT_TARGET_AGE
)
from src.aging import age_photo


# ============== Pydantic Models ==============

class AgePhotoRequest(BaseModel):
    """Age photo request with base64 image"""
    image_base64: str
    target_age: int = DEFAULT_TARGET_AGE
    mock: bool = True


class AgePhotoResponse(BaseModel):
    """Age photo response"""
    success: bool
    message: str
    original_path: Optional[str] = None
    aged_path: Optional[str] = None
    aged_image_base64: Optional[str] = None


class StatusResponse(BaseModel):
    """System status response"""
    status: str
    gpu_available: bool
    gpu_name: Optional[str] = None
    mock_mode: bool
    camera_available: bool
    version: str = "1.0.0"


# ============== Lifespan Handler ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("\n" + "=" * 60)
    print("  SAGE API Server Starting...")
    print("=" * 60)

    # Check GPU
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("  GPU: Not available (using CPU)")
    except ImportError:
        print("  GPU: PyTorch not installed")

    mode = "Mock" if (MOCK_MODE or AUTO_MOCK) else "Production"
    print(f"  Mode: {mode}")
    print("=" * 60 + "\n")

    yield

    # Cleanup
    print("\n  SAGE API Server Shutting down...")


# ============== FastAPI App ==============

app = FastAPI(
    title="SAGE API",
    description="Self-Aging Generative Experience - Remote API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for remote access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "name": "SAGE API",
        "description": "Self-Aging Generative Experience",
        "version": "1.0.0",
        "endpoints": {
            "status": "/status",
            "age_photo": "/age/photo",
            "age_upload": "/age/upload"
        }
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get system status"""
    # Check GPU
    gpu_available = False
    gpu_name = None
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    # Check camera
    camera_available = False
    try:
        cap = cv2.VideoCapture(0)
        camera_available = cap.isOpened()
        cap.release()
    except:
        pass

    return StatusResponse(
        status="online",
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        mock_mode=MOCK_MODE or AUTO_MOCK,
        camera_available=camera_available
    )


@app.post("/age/upload", response_model=AgePhotoResponse)
async def age_upload(
    file: UploadFile = File(...),
    target_age: int = Form(default=DEFAULT_TARGET_AGE),
    mock: bool = Form(default=True)
):
    """
    Upload and age a photo

    - **file**: Image file (JPEG/PNG)
    - **target_age**: Target age (default: 75)
    - **mock**: Use mock mode (default: True)
    """
    try:
        # Read uploaded file
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image file")

        # Save original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = f"upload_{timestamp}.jpg"
        original_path = CAPTURED_DIR / original_filename
        cv2.imwrite(str(original_path), image)

        # Process aging
        use_mock = mock or AUTO_MOCK
        aged_path = age_photo(str(original_path), target_age, mock=use_mock)

        if aged_path is None:
            raise HTTPException(status_code=500, detail="Aging process failed")

        # Read aged image and convert to base64
        aged_image = cv2.imread(str(aged_path))
        _, buffer = cv2.imencode('.jpg', aged_image)
        aged_base64 = base64.b64encode(buffer).decode('utf-8')

        return AgePhotoResponse(
            success=True,
            message="Photo aged successfully",
            original_path=str(original_path),
            aged_path=str(aged_path),
            aged_image_base64=aged_base64
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/age/photo", response_model=AgePhotoResponse)
async def age_photo_base64(request: AgePhotoRequest):
    """
    Age a photo from base64 encoded image

    - **image_base64**: Base64 encoded image
    - **target_age**: Target age (default: 75)
    - **mock**: Use mock mode (default: True)
    """
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(status_code=400, detail="Invalid base64 image")

        # Save original
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = f"api_{timestamp}.jpg"
        original_path = CAPTURED_DIR / original_filename
        cv2.imwrite(str(original_path), image)

        # Process aging
        # 如果 GPU 不可用且未明確指定使用真實模型，自動使用 mock 模式
        from config.settings import has_cuda
        gpu_available = has_cuda()
        
        if request.mock is False and not gpu_available:
            print(f"[SAGE API] GPU 不可用，自動切換到 Mock 模式")
            use_mock = True
        else:
            use_mock = request.mock or AUTO_MOCK
        
        print(f"[SAGE API] 開始變老處理: target_age={request.target_age}, mock={use_mock}, gpu_available={gpu_available}")
        
        try:
            aged_path = age_photo(str(original_path), request.target_age, mock=use_mock)
        except Exception as e:
            print(f"[SAGE API] 變老處理異常: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"變老處理失敗: {str(e)}")

        if aged_path is None:
            print("[SAGE API] 變老處理返回 None")
            raise HTTPException(status_code=500, detail="Aging process failed: age_photo returned None")

        # Read aged image and convert to base64
        aged_image = cv2.imread(str(aged_path))
        _, buffer = cv2.imencode('.jpg', aged_image)
        aged_base64 = base64.b64encode(buffer).decode('utf-8')

        return AgePhotoResponse(
            success=True,
            message="Photo aged successfully",
            original_path=str(original_path),
            aged_path=str(aged_path),
            aged_image_base64=aged_base64
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/age/result/{filename}")
async def get_aged_result(filename: str):
    """Download aged photo result"""
    file_path = AGED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), media_type="image/jpeg")


# ============== Main Entry ==============

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server"""
    import uvicorn

    print(f"\n  Starting SAGE API Server at http://{host}:{port}")
    print(f"  API Documentation: http://{host}:{port}/docs")
    print(f"  Press Ctrl+C to stop\n")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")

    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
