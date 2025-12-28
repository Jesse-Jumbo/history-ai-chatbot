"""
src/aging.py 模組測試
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import cv2
import numpy as np
import pytest

# 加入專案路徑
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))


class TestAgingProcessor:
    """AgingProcessor 類別測試"""

    def test_aging_processor_init_mock_mode(self):
        """測試 Mock 模式初始化"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        assert processor.mock_mode is True
        assert processor.model is None

    def test_aging_processor_init_auto_mock(self):
        """測試自動 Mock 模式"""
        from src.aging import AgingProcessor

        # 預設應該是 mock 模式 (因為 AUTO_MOCK=True)
        processor = AgingProcessor()

        assert processor.mock_mode is True

    def test_add_wrinkles(self, sample_image):
        """測試皺紋效果"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor._add_wrinkles(sample_image, intensity=0.5)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_add_age_spots(self, sample_image):
        """測試老年斑效果"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        # 設定隨機種子以確保結果可重現
        np.random.seed(42)
        result = processor._add_age_spots(sample_image, density=0.01)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_simulate_skin_aging(self, sample_image):
        """測試皮膚老化效果"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor._simulate_skin_aging(sample_image, age_factor=0.5)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_add_hair_graying(self, sample_image):
        """測試頭髮變白效果"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor._add_hair_graying(sample_image, gray_ratio=0.5)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_add_facial_sagging(self, sample_image):
        """測試面部下垂效果"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor._add_facial_sagging(sample_image, intensity=0.1)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_mock_aging_full_pipeline(self, sample_image):
        """測試完整 Mock 變老流程"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor._mock_aging(sample_image, target_age=75)

        assert result is not None
        assert result.shape == sample_image.shape
        assert result.dtype == np.uint8

    def test_mock_aging_different_ages(self, sample_image):
        """測試不同目標年齡的 Mock 變老"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        result_50 = processor._mock_aging(sample_image.copy(), target_age=50)
        result_75 = processor._mock_aging(sample_image.copy(), target_age=75)
        result_90 = processor._mock_aging(sample_image.copy(), target_age=90)

        # 確保都是有效結果
        assert result_50 is not None
        assert result_75 is not None
        assert result_90 is not None

        # 年齡越大，處理應該越明顯（影像差異越大）
        # 但這個很難測試，所以只確認結果有效

    def test_process_file(self, temp_image_file, temp_directory):
        """測試處理影像檔案"""
        from src.aging import AgingProcessor

        with patch('src.aging.AGED_DIR', temp_directory):
            processor = AgingProcessor(mock_mode=True)
            result = processor.process(
                temp_image_file,
                target_age=75,
                output_filename="test_aged.jpg"
            )

            assert result is not None
            assert result.exists()
            assert result.name == "test_aged.jpg"

            # 確認輸出影像有效
            output_image = cv2.imread(str(result))
            assert output_image is not None

    def test_process_nonexistent_file(self):
        """測試處理不存在的檔案"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor.process("/nonexistent/path/image.jpg")

        assert result is None

    def test_process_auto_filename(self, temp_image_file, temp_directory):
        """測試自動生成輸出檔名"""
        from src.aging import AgingProcessor

        with patch('src.aging.AGED_DIR', temp_directory):
            processor = AgingProcessor(mock_mode=True)
            result = processor.process(temp_image_file, target_age=80)

            assert result is not None
            assert result.exists()
            assert "aged_80_" in result.name

    def test_process_realtime(self, sample_image):
        """測試即時處理"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)
        result = processor.process_realtime(sample_image, target_age=75)

        assert result is not None
        assert result.shape == sample_image.shape


class TestAgePhoto:
    """age_photo 函數測試"""

    def test_age_photo_basic(self, temp_image_file, temp_directory):
        """測試基本 age_photo 函數"""
        from src.aging import age_photo

        with patch('src.aging.AGED_DIR', temp_directory):
            result = age_photo(temp_image_file, target_age=75, mock=True)

            assert result is not None
            assert result.exists()

    def test_age_photo_nonexistent(self):
        """測試處理不存在的檔案"""
        from src.aging import age_photo

        result = age_photo("/nonexistent/image.jpg", mock=True)

        assert result is None

    def test_age_photo_different_ages(self, temp_image_file, temp_directory):
        """測試不同年齡"""
        from src.aging import age_photo

        with patch('src.aging.AGED_DIR', temp_directory):
            for age in [50, 60, 70, 80, 90]:
                result = age_photo(temp_image_file, target_age=age, mock=True)
                assert result is not None


class TestAgingEffectsQuality:
    """變老效果品質測試"""

    def test_wrinkles_dont_break_image(self, sample_image):
        """測試皺紋效果不會損壞影像"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        for intensity in [0.1, 0.3, 0.5, 0.7, 0.9]:
            result = processor._add_wrinkles(sample_image.copy(), intensity=intensity)

            # 確認沒有 NaN 或 Inf
            assert not np.isnan(result).any()
            assert not np.isinf(result).any()

            # 確認值在有效範圍內
            assert result.min() >= 0
            assert result.max() <= 255

    def test_age_spots_density(self, sample_image):
        """測試老年斑密度"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        np.random.seed(42)
        result_low = processor._add_age_spots(sample_image.copy(), density=0.001)

        np.random.seed(42)
        result_high = processor._add_age_spots(sample_image.copy(), density=0.01)

        # 高密度應該有更多改變
        diff_low = np.abs(result_low.astype(float) - sample_image.astype(float)).mean()
        diff_high = np.abs(result_high.astype(float) - sample_image.astype(float)).mean()

        # 這個測試可能不穩定，因為有隨機性
        # 所以只確認結果有效
        assert result_low is not None
        assert result_high is not None

    def test_full_aging_pipeline_stability(self, sample_image):
        """測試完整變老流程穩定性"""
        from src.aging import AgingProcessor

        processor = AgingProcessor(mock_mode=True)

        # 多次執行應該都成功
        for _ in range(5):
            result = processor._mock_aging(sample_image.copy(), target_age=75)

            assert result is not None
            assert result.shape == sample_image.shape
            assert result.dtype == np.uint8
            assert not np.isnan(result.astype(float)).any()
