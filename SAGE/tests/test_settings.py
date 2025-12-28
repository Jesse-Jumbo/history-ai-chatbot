"""
config/settings.py 模組測試
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestSettings:
    """設定模組測試"""

    def test_base_dir_exists(self):
        """測試 BASE_DIR 路徑正確"""
        from config.settings import BASE_DIR
        assert BASE_DIR.exists()
        assert BASE_DIR.is_dir()

    def test_assets_directories_exist(self):
        """測試資源目錄存在"""
        from config.settings import ASSETS_DIR, CAPTURED_DIR, AGED_DIR, MODELS_DIR

        assert ASSETS_DIR.exists()
        assert CAPTURED_DIR.exists()
        assert AGED_DIR.exists()
        assert MODELS_DIR.exists()

    def test_camera_settings(self):
        """測試攝影機設定值"""
        from config.settings import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT

        assert isinstance(CAMERA_INDEX, int)
        assert CAMERA_INDEX >= 0
        assert CAMERA_WIDTH > 0
        assert CAMERA_HEIGHT > 0
        assert CAMERA_WIDTH == 1280
        assert CAMERA_HEIGHT == 720

    def test_fading_settings(self):
        """測試 FADING 模型設定"""
        from config.settings import FADING_MODEL_PATH, FADING_CONFIG, DEFAULT_TARGET_AGE

        assert isinstance(FADING_MODEL_PATH, Path)
        assert DEFAULT_TARGET_AGE > 0
        assert DEFAULT_TARGET_AGE == 75

        # FADING 配置參數
        assert "num_ddim_steps" in FADING_CONFIG
        assert "guidance_scale" in FADING_CONFIG
        assert "image_size" in FADING_CONFIG
        assert FADING_CONFIG["image_size"] == 512

    def test_mock_mode_default(self):
        """測試 Mock 模式預設值"""
        from config.settings import AUTO_MOCK

        # 預設應該是 False（需要明確設定環境變數才開啟）
        assert AUTO_MOCK is False

    def test_age_range(self):
        """測試年齡範圍設定"""
        from config.settings import AGE_MIN, AGE_MAX

        assert AGE_MIN == 0
        assert AGE_MAX == 100

    def test_model_paths(self):
        """測試模型路徑配置"""
        from config.settings import MODEL_PATHS, check_model_exists, get_model_path

        assert "fading" in MODEL_PATHS
        assert "mediapipe_landmarker" in MODEL_PATHS

        # 測試函數
        assert isinstance(check_model_exists("fading"), bool)
        fading_path = get_model_path("fading")
        assert fading_path is not None

    def test_get_device_function(self):
        """測試 get_device 函數"""
        from config.settings import get_device

        device = get_device()
        # 可能返回 None（如果 torch 未安裝）或 torch.device
        if device is not None:
            import torch
            assert isinstance(device, torch.device)

    def test_has_cuda_function(self):
        """測試 has_cuda 函數"""
        from config.settings import has_cuda

        result = has_cuda()
        assert isinstance(result, bool)

    def test_mock_mode_from_env(self):
        """測試從環境變數讀取 Mock 模式"""
        # 設定環境變數為 true
        with patch.dict(os.environ, {'SAGE_MOCK_MODE': 'true'}):
            # 需要重新載入模組才能讀取新的環境變數
            import importlib
            import config.settings as settings
            importlib.reload(settings)
            assert settings.MOCK_MODE is True

        # 測試完後還原
        with patch.dict(os.environ, {'SAGE_MOCK_MODE': 'false'}):
            import importlib
            import config.settings as settings
            importlib.reload(settings)
            assert settings.MOCK_MODE is False

    def test_directories_created_on_import(self):
        """測試導入模組時自動建立目錄"""
        from config.settings import CAPTURED_DIR, AGED_DIR, MODELS_DIR

        # 這些目錄應該在導入時自動建立
        assert CAPTURED_DIR.is_dir()
        assert AGED_DIR.is_dir()
        assert MODELS_DIR.is_dir()

    def test_aging_engine_setting(self):
        """測試老化引擎設定"""
        from config.settings import AGING_ENGINE

        assert AGING_ENGINE in ["fading", "mock"]
