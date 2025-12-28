"""
SAGE 測試配置 - pytest fixtures 和共用設定
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "config"))


@pytest.fixture
def sample_image():
    """建立測試用影像 (640x480 BGR)"""
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    # 加入一些顏色和圖案
    image[:, :, 2] = 100  # 紅色背景
    # 畫一個模擬臉部的圓形
    cv2.circle(image, (320, 240), 100, (200, 180, 160), -1)
    return image


@pytest.fixture
def sample_image_with_face():
    """建立帶有可偵測人臉的測試影像"""
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    # 建立一個類似人臉的區域（淺色皮膚）
    cv2.ellipse(image, (320, 200), (80, 100), 0, 0, 360, (180, 200, 220), -1)
    # 眼睛
    cv2.circle(image, (290, 170), 15, (80, 80, 80), -1)
    cv2.circle(image, (350, 170), 15, (80, 80, 80), -1)
    # 嘴巴
    cv2.ellipse(image, (320, 240), (30, 15), 0, 0, 180, (100, 100, 150), -1)
    return image


@pytest.fixture
def temp_image_file(sample_image):
    """建立暫存影像檔案"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        temp_path = Path(f.name)
    cv2.imwrite(str(temp_path), sample_image)
    yield temp_path
    # 清理
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_directory():
    """建立暫存目錄"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_camera():
    """模擬攝影機"""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
    return mock_cap


@pytest.fixture
def mock_env_vars():
    """設定測試用環境變數"""
    original_env = os.environ.copy()
    os.environ['SAGE_MOCK_MODE'] = 'true'
    os.environ['GEMINI_API_KEY'] = 'test_api_key'
    yield
    # 還原
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_gemini():
    """模擬 Gemini API"""
    with patch('src.chat.GEMINI_AVAILABLE', True):
        with patch('src.chat.genai') as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_result = MagicMock()
            mock_result.text = "這是來自模擬 Gemini 的回應。"
            mock_client.models.generate_content.return_value = mock_result
            yield mock_client
