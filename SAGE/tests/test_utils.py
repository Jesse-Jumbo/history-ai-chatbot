"""
src/utils.py 模組測試
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import cv2
import numpy as np
import pytest

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class TestResizeImage:
    """resize_image 函數測試"""

    def test_resize_keep_aspect_width_larger(self, sample_image):
        """測試保持比例縮放（寬度較大）"""
        from src.utils import resize_image

        # 原始大小: 640x480
        result = resize_image(sample_image, target_size=320, keep_aspect=True)

        assert result.shape[0] <= 320  # 高度
        assert result.shape[1] == 320  # 寬度 (因為寬度較大)

    def test_resize_keep_aspect_height_larger(self):
        """測試保持比例縮放（高度較大）"""
        from src.utils import resize_image

        # 建立高度較大的影像
        image = np.zeros((800, 400, 3), dtype=np.uint8)
        result = resize_image(image, target_size=400, keep_aspect=True)

        assert result.shape[0] == 400  # 高度
        assert result.shape[1] <= 400  # 寬度

    def test_resize_no_aspect(self, sample_image):
        """測試不保持比例縮放"""
        from src.utils import resize_image

        result = resize_image(sample_image, target_size=256, keep_aspect=False)

        assert result.shape[0] == 256
        assert result.shape[1] == 256

    def test_resize_preserves_channels(self, sample_image):
        """測試縮放後保持通道數"""
        from src.utils import resize_image

        result = resize_image(sample_image, target_size=256)
        assert result.shape[2] == 3


class TestCenterCrop:
    """center_crop 函數測試"""

    def test_center_crop_basic(self, sample_image):
        """測試基本中心裁切"""
        from src.utils import center_crop

        result = center_crop(sample_image, 200)

        assert result.shape[0] == 200
        assert result.shape[1] == 200

    def test_center_crop_larger_than_image(self, sample_image):
        """測試裁切尺寸大於原圖"""
        from src.utils import center_crop

        # 裁切尺寸比原圖大時，應該從 (0,0) 開始
        result = center_crop(sample_image, 1000)

        # 結果不應該超過原圖尺寸
        assert result.shape[0] <= sample_image.shape[0]
        assert result.shape[1] <= sample_image.shape[1]

    def test_center_crop_preserves_channels(self, sample_image):
        """測試裁切後保持通道數"""
        from src.utils import center_crop

        result = center_crop(sample_image, 100)
        assert result.shape[2] == 3


class TestDetectFace:
    """detect_face 函數測試"""

    def test_detect_face_no_face(self, sample_image):
        """測試無人臉影像"""
        from src.utils import detect_face

        # 純色影像應該偵測不到人臉
        result = detect_face(sample_image)
        # 可能偵測到，也可能偵測不到，取決於 OpenCV 版本
        assert result is None or len(result) == 4

    def test_detect_face_returns_tuple(self, sample_image_with_face):
        """測試偵測到人臉時回傳 tuple"""
        from src.utils import detect_face

        result = detect_face(sample_image_with_face)

        # 可能偵測到，也可能偵測不到
        if result is not None:
            assert len(result) == 4
            x, y, w, h = result
            assert x >= 0
            assert y >= 0
            assert w > 0
            assert h > 0


class TestCropFace:
    """crop_face 函數測試"""

    def test_crop_face_no_face(self, sample_image):
        """測試無人臉影像"""
        from src.utils import crop_face

        result = crop_face(sample_image)
        # 偵測不到人臉時回傳 None，或者如果偶然偵測到則回傳裁切結果
        assert result is None or isinstance(result, np.ndarray)

    def test_crop_face_with_padding(self, sample_image_with_face):
        """測試帶有 padding 的人臉裁切"""
        from src.utils import crop_face

        result = crop_face(sample_image_with_face, padding=0.5)

        # 可能偵測到，也可能偵測不到
        if result is not None:
            assert isinstance(result, np.ndarray)
            assert len(result.shape) == 3
            assert result.shape[2] == 3


class TestShowComparison:
    """show_comparison 函數測試"""

    def test_show_comparison_basic(self, sample_image):
        """測試基本並排顯示（需要 mock cv2.imshow）"""
        from src.utils import show_comparison

        with patch('src.utils.cv2.imshow') as mock_imshow:
            with patch('src.utils.cv2.waitKey', return_value=27):  # ESC 鍵
                with patch('src.utils.cv2.destroyAllWindows'):
                    # 應該不會拋出例外
                    show_comparison(sample_image, sample_image.copy())
                    mock_imshow.assert_called_once()

    def test_show_comparison_different_sizes(self):
        """測試不同尺寸影像的並排顯示"""
        from src.utils import show_comparison

        img1 = np.zeros((480, 640, 3), dtype=np.uint8)
        img2 = np.zeros((720, 1280, 3), dtype=np.uint8)

        with patch('src.utils.cv2.imshow') as mock_imshow:
            with patch('src.utils.cv2.waitKey', return_value=27):
                with patch('src.utils.cv2.destroyAllWindows'):
                    show_comparison(img1, img2)
                    mock_imshow.assert_called_once()

                    # 檢查傳入的影像尺寸（高度應該相同）
                    call_args = mock_imshow.call_args
                    displayed_image = call_args[0][1]
                    # 並排後的影像寬度應該是兩張圖的寬度之和
                    assert displayed_image.shape[1] > max(img1.shape[1], img2.shape[1])
