"""
SAGE 設定檔
使用 FADING (Face Aging via Diffusion-based Editing)
基於 https://github.com/gh-BumsooKim/FADING_stable
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# 引擎選擇
# =============================================================================
# 可選: "fading", "mock"
AGING_ENGINE = os.getenv("SAGE_AGING_ENGINE", "fading")

# =============================================================================
# 專案目錄結構
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# 資源目錄
ASSETS_DIR = BASE_DIR / "assets"
CAPTURED_DIR = ASSETS_DIR / "captured"
AGED_DIR = ASSETS_DIR / "aged"
MODELS_DIR = BASE_DIR / "models"

# 確保目錄存在
CAPTURED_DIR.mkdir(parents=True, exist_ok=True)
AGED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 攝影機設定
# =============================================================================
CAMERA_INDEX = int(os.getenv("SAGE_CAMERA_INDEX", "0"))
CAMERA_WIDTH = int(os.getenv("SAGE_CAMERA_WIDTH", "1280"))
CAMERA_HEIGHT = int(os.getenv("SAGE_CAMERA_HEIGHT", "720"))

# =============================================================================
# FADING 設定 (Face Aging via Diffusion-based Editing)
# 基於 https://github.com/gh-BumsooKim/FADING_stable
# =============================================================================

# FADING 模型目錄
FADING_MODEL_PATH = MODELS_DIR / "finetune_double_prompt_150_random"
FADING_CODE_PATH = BASE_DIR / "src" / "fading"

# FADING 配置參數
FADING_CONFIG = {
    # 擴散模型設定
    "num_ddim_steps": 100,  # DDIM 步數
    "guidance_scale": 7.5,  # CFG 引導強度

    # 影像設定
    "image_size": 512,  # 輸入/輸出影像大小

    # 推理設定
    "cross_replace_steps": 0.8,  # 交叉注意力替換步驟
    "self_replace_steps": 0.5,  # 自注意力替換步驟

    # 預設目標年齡
    "default_target_ages": [10, 20, 40, 60, 80],
}

# 年齡範圍
AGE_MIN = 0
AGE_MAX = 100

# 預設目標年齡
DEFAULT_TARGET_AGE = int(os.getenv("SAGE_TARGET_AGE", "75"))

# =============================================================================
# 人臉偵測模型路徑
# =============================================================================
MODEL_PATHS = {
    # FADING 模型
    "fading": FADING_MODEL_PATH,

    # MediaPipe Face Landmarker
    "mediapipe_landmarker": MODELS_DIR / "face_landmarker.task",
}

# 模型下載 URL
MODEL_URLS = {
    # MediaPipe Face Landmarker
    "mediapipe_landmarker": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
}

# =============================================================================
# 模式設定
# =============================================================================

# Mock 模式（開發用）
MOCK_MODE = os.getenv("SAGE_MOCK_MODE", "false").lower() == "true"

# 自動 Mock 模式
# True: 預設使用 Mock 模式（CPU 影像處理效果）
# False: 嘗試使用 GPU 模型
AUTO_MOCK = os.getenv("SAGE_AUTO_MOCK", "false").lower() == "true"


def has_cuda():
    """檢查 CUDA 是否可用"""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def get_device():
    """取得運算裝置"""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            return torch.device("cpu")
    except Exception:
        return None


def check_model_exists(model_name: str) -> bool:
    """檢查模型是否存在"""
    if model_name in MODEL_PATHS:
        return MODEL_PATHS[model_name].exists()
    return False


def get_model_path(model_name: str) -> Path:
    """取得模型路徑"""
    if model_name in MODEL_PATHS:
        return MODEL_PATHS[model_name]
    raise ValueError(f"Unknown model: {model_name}")


# =============================================================================
# API 伺服器設定
# =============================================================================
API_HOST = os.getenv("SAGE_API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("SAGE_API_PORT", "8000"))
API_RELOAD = os.getenv("SAGE_API_RELOAD", "false").lower() == "true"

# =============================================================================
# 日誌設定
# =============================================================================
LOG_LEVEL = os.getenv("SAGE_LOG_LEVEL", "INFO")
