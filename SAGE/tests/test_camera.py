"""
src/camera.py 模組測試
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import cv2
import numpy as np
import pytest

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class TestCamera:
    """Camera 類別測試"""

    def test_camera_init(self):
        """測試 Camera 初始化"""
        from src.camera import Camera

        camera = Camera(camera_index=0)

        assert camera.camera_index == 0
        assert camera.cap is None
        assert camera.is_opened is False

    def test_camera_init_custom_index(self):
        """測試自訂攝影機索引"""
        from src.camera import Camera

        camera = Camera(camera_index=2)
        assert camera.camera_index == 2

    def test_camera_open_success(self, mock_camera):
        """測試成功開啟攝影機"""
        from src.camera import Camera

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            result = camera.open()

            assert result is True
            assert camera.is_opened is True

    def test_camera_open_failure(self):
        """測試開啟攝影機失敗"""
        from src.camera import Camera

        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        with patch('src.camera.cv2.VideoCapture', return_value=mock_cap):
            camera = Camera()
            result = camera.open()

            assert result is False
            assert camera.is_opened is False

    def test_camera_close(self, mock_camera):
        """測試關閉攝影機"""
        from src.camera import Camera

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            camera.open()
            camera.close()

            mock_camera.release.assert_called_once()
            assert camera.is_opened is False

    def test_camera_read_frame(self, mock_camera):
        """測試讀取幀"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_camera.read.return_value = (True, test_frame)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            camera.open()
            frame = camera.read_frame()

            assert frame is not None
            assert frame.shape == (720, 1280, 3)

    def test_camera_read_frame_failure(self, mock_camera):
        """測試讀取幀失敗"""
        from src.camera import Camera

        mock_camera.read.return_value = (False, None)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            camera.open()
            frame = camera.read_frame()

            assert frame is None

    def test_camera_read_frame_not_opened(self):
        """測試未開啟時讀取幀"""
        from src.camera import Camera

        camera = Camera()
        frame = camera.read_frame()

        assert frame is None

    def test_camera_capture_photo(self, mock_camera, temp_directory):
        """測試拍照並儲存"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        test_frame[:, :, 1] = 128  # 加點綠色
        mock_camera.read.return_value = (True, test_frame)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            with patch('src.camera.CAPTURED_DIR', temp_directory):
                camera = Camera()
                camera.open()
                result = camera.capture_photo(filename="test_capture.jpg")

                assert result is not None
                assert result.exists()
                assert result.name == "test_capture.jpg"

    def test_camera_capture_photo_auto_filename(self, mock_camera, temp_directory):
        """測試自動生成檔名拍照"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_camera.read.return_value = (True, test_frame)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            with patch('src.camera.CAPTURED_DIR', temp_directory):
                camera = Camera()
                camera.open()
                result = camera.capture_photo()

                assert result is not None
                assert result.exists()
                assert result.name.startswith("capture_")
                assert result.suffix == ".jpg"

    def test_camera_context_manager(self, mock_camera):
        """測試 context manager (with 語法)"""
        from src.camera import Camera

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            with Camera() as cam:
                assert cam.is_opened is True

            mock_camera.release.assert_called_once()


class TestCameraUI:
    """Camera UI 相關測試"""

    def test_draw_ui_overlay(self, mock_camera):
        """測試 UI 覆蓋層繪製"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            camera.open()

            # 呼叫私有方法測試
            result = camera._draw_ui_overlay(
                test_frame,
                message="Test Message",
                sub_message="Sub message",
                show_guide=True,
                mirror=True
            )

            assert result is not None
            assert result.shape == test_frame.shape

    def test_draw_countdown(self, mock_camera):
        """測試倒數計時畫面繪製"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            camera = Camera()
            camera.open()

            result = camera._draw_countdown(test_frame, count=3, mirror=True)

            assert result is not None
            assert result.shape == test_frame.shape

    def test_draw_flash(self):
        """測試閃光效果繪製"""
        from src.camera import Camera

        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        camera = Camera()

        result = camera._draw_flash(test_frame)

        assert result is not None
        assert result.shape == test_frame.shape
        # 閃光效果應該讓影像變亮
        assert result.mean() > test_frame.mean()


class TestQuickCapture:
    """quick_capture 函數測試"""

    def test_quick_capture_mock(self, mock_camera, temp_directory):
        """測試 quick_capture 函數"""
        from src.camera import quick_capture

        # 模擬按下 ESC 取消
        with patch('src.camera.cv2.VideoCapture', return_value=mock_camera):
            with patch('src.camera.cv2.waitKey', return_value=27):  # ESC
                with patch('src.camera.cv2.imshow'):
                    with patch('src.camera.cv2.destroyAllWindows'):
                        result = quick_capture()

                        # ESC 取消應該回傳 None
                        assert result is None


class TestCameraColors:
    """攝影機顏色常數測試"""

    def test_colors_defined(self):
        """測試顏色常數已定義"""
        from src.camera import (
            COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING,
            COLOR_COUNTDOWN, COLOR_WHITE, COLOR_BLACK, COLOR_OVERLAY
        )

        assert len(COLOR_PRIMARY) == 3
        assert len(COLOR_SUCCESS) == 3
        assert len(COLOR_WARNING) == 3
        assert len(COLOR_COUNTDOWN) == 3
        assert len(COLOR_WHITE) == 3
        assert len(COLOR_BLACK) == 3
        assert len(COLOR_OVERLAY) == 3

        # 確認是 BGR 格式 (0-255)
        for color in [COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WHITE, COLOR_BLACK]:
            assert all(0 <= c <= 255 for c in color)
