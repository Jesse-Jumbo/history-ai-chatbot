"""
人臉變老模組 - 使用 FADING (Face Aging via Diffusion-based Editing)
基於 https://github.com/gh-BumsooKim/FADING_stable
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Union, List
from datetime import datetime
from PIL import Image

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    AGED_DIR,
    MOCK_MODE,
    AGE_MIN,
    AGE_MAX,
    AGING_ENGINE,
    FADING_MODEL_PATH,
    FADING_CODE_PATH,
    FADING_CONFIG,
)


class FADINGProcessor:
    """FADING 人臉變老處理器 - 基於擴散模型"""

    def __init__(self):
        """初始化 FADING 處理器"""
        self.model = None
        self.null_inversion = None
        self.tokenizer = None
        self.device = None
        self._initialized = False

    def _load_model(self):
        """載入 FADING 擴散模型"""
        if self._initialized:
            return True

        try:
            import torch
            from diffusers import StableDiffusionPipeline, DDIMScheduler

            # 檢查模型是否存在
            if not FADING_MODEL_PATH.exists():
                print(f"FADING 模型不存在: {FADING_MODEL_PATH}")
                print("   請執行下載腳本或手動下載模型")
                return False

            self.device = torch.device('cuda:0') if torch.cuda.is_available() else torch.device('cpu')
            print(f"[FADING] 使用裝置: {self.device}")

            # 設定 DDIM scheduler
            scheduler = DDIMScheduler(
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear",
                clip_sample=False,
                set_alpha_to_one=False,
                steps_offset=1
            )

            # 載入擴散模型
            print(f"[FADING] 載入模型: {FADING_MODEL_PATH}")
            
            # 允許使用 pickle 格式（如果沒有 safetensors）
            # 設置環境變數以允許不安全的載入（僅用於本地模型）
            import os
            original_safe_loading = os.environ.get('TRANSFORMERS_SAFE_LOADING', None)
            os.environ['TRANSFORMERS_SAFE_LOADING'] = 'false'
            
            try:
                self.model = StableDiffusionPipeline.from_pretrained(
                    str(FADING_MODEL_PATH),
                    scheduler=scheduler,
                    safety_checker=None,
                    use_safetensors=False,  # 允許使用 pickle 格式
                    local_files_only=True   # 只使用本地文件
                ).to(self.device)
            finally:
                # 恢復原始設置
                if original_safe_loading is None:
                    os.environ.pop('TRANSFORMERS_SAFE_LOADING', None)
                else:
                    os.environ['TRANSFORMERS_SAFE_LOADING'] = original_safe_loading

            self.tokenizer = self.model.tokenizer

            # 載入 FADING 工具
            sys.path.insert(0, str(FADING_CODE_PATH))
            from null_inversion import NullInversion
            self.null_inversion = NullInversion(self.model)

            self._initialized = True
            print(f"[FADING] 模型載入完成")

            if self.device.type == 'cuda':
                import torch
                gpu_name = torch.cuda.get_device_name(0)
                print(f"   GPU: {gpu_name}")

            return True

        except Exception as e:
            print(f"[FADING] 模型載入失敗: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _get_person_placeholder(self, age: int, gender: str) -> str:
        """根據年齡和性別取得人物描述詞"""
        is_female = gender.lower() == 'female'
        if age <= 15:
            return 'girl' if is_female else 'boy'
        else:
            return 'woman' if is_female else 'man'

    def process(
        self,
        image_path: Union[str, Path],
        target_age: int = 75,
        initial_age: int = 25,
        gender: str = "male",
        output_filename: Optional[str] = None
    ) -> Optional[Path]:
        """
        使用 FADING 處理人臉變老

        Args:
            image_path: 輸入影像路徑
            target_age: 目標年齡
            initial_age: 估計的原始年齡
            gender: 性別 ("male" 或 "female")
            output_filename: 輸出檔名

        Returns:
            輸出影像路徑
        """
        import torch

        image_path = Path(image_path)
        if not image_path.exists():
            print(f"影像不存在: {image_path}")
            return None

        # 載入模型
        if not self._load_model():
            print("[FADING] 模型載入失敗，無法處理")
            return None

        print(f"[FADING] 處理影像: {image_path}")
        print(f"   初始年齡: {initial_age}, 目標年齡: {target_age}, 性別: {gender}")

        # 建立提示詞
        person_placeholder = self._get_person_placeholder(initial_age, gender)
        inversion_prompt = f"photo of {initial_age} year old {person_placeholder}"
        print(f"   反演提示詞: {inversion_prompt}")

        # Null-text 反演
        print("   執行 Null-text 反演...")
        sys.path.insert(0, str(FADING_CODE_PATH))
        from null_inversion import load_512
        from p2p import make_controller, p2p_text2image

        try:
            (image_gt, image_enc), x_t, uncond_embeddings = self.null_inversion.invert(
                str(image_path),
                inversion_prompt,
                offsets=(0, 0, 0, 0),
                verbose=True
            )
        except Exception as e:
            print(f"   Null-text 反演失敗: {e}")
            return None

        # 年齡編輯
        print(f"   年齡編輯: {initial_age} -> {target_age}...")
        new_person_placeholder = self._get_person_placeholder(target_age, gender)
        new_prompt = inversion_prompt.replace(person_placeholder, new_person_placeholder)
        new_prompt = new_prompt.replace(str(initial_age), str(target_age))

        blend_word = (((str(initial_age), person_placeholder,), (str(target_age), new_person_placeholder,)))
        prompts = [inversion_prompt, new_prompt]

        cross_replace_steps = {'default_': FADING_CONFIG["cross_replace_steps"]}
        self_replace_steps = FADING_CONFIG["self_replace_steps"]
        eq_params = {"words": (str(target_age)), "values": (1,)}

        g_cuda = torch.Generator(device=self.device)

        controller = make_controller(
            prompts, True, cross_replace_steps, self_replace_steps,
            self.tokenizer, blend_word, eq_params
        )

        images, _ = p2p_text2image(
            self.model, prompts, controller,
            generator=g_cuda.manual_seed(0),
            latent=x_t,
            uncond_embeddings=uncond_embeddings
        )

        # 儲存結果
        new_img = images[-1]
        new_img_pil = Image.fromarray(new_img)

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"aged_{target_age}_{timestamp}.png"

        output_path = AGED_DIR / output_filename
        new_img_pil.save(str(output_path))
        print(f"   結果已儲存: {output_path}")

        return output_path

    def process_multiple_ages(
        self,
        image_path: Union[str, Path],
        target_ages: List[int] = None,
        initial_age: int = 25,
        gender: str = "male"
    ) -> List[Path]:
        """
        使用 FADING 處理多個目標年齡

        Args:
            image_path: 輸入影像路徑
            target_ages: 目標年齡列表
            initial_age: 估計的原始年齡
            gender: 性別

        Returns:
            輸出影像路徑列表
        """
        if target_ages is None:
            target_ages = FADING_CONFIG["default_target_ages"]

        results = []
        for age in target_ages:
            result = self.process(image_path, age, initial_age, gender)
            if result:
                results.append(result)

        return results


class MockProcessor:
    """Mock 處理器 - 使用 CPU 影像處理模擬老化效果（開發用）"""

    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        print("[Mock Mode] 變老處理器已啟動（模擬模式）")

    def _detect_face(self, image: np.ndarray):
        """偵測人臉位置"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 調整參數以提高偵測率：降低 minSize，調整 scaleFactor 和 minNeighbors
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.05,  # 降低縮放因子，更細緻的掃描
            minNeighbors=3,     # 降低鄰居數，提高敏感度
            minSize=(50, 50)    # 降低最小尺寸，可以偵測更小的人臉
        )
        if len(faces) == 0:
            print("   嘗試使用更寬鬆的參數重新偵測...")
            # 如果第一次失敗，使用更寬鬆的參數
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.03,
                minNeighbors=2,
                minSize=(30, 30)
            )
        if len(faces) == 0:
            return None
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        return tuple(faces[0])

    def _create_face_mask(self, image: np.ndarray, face_rect, expand: float = 0.3):
        """建立臉部遮罩"""
        h, w = image.shape[:2]
        x, y, fw, fh = face_rect
        cx = x + fw // 2
        cy = y + fh // 2
        rx = int(fw * (0.5 + expand))
        ry = int(fh * (0.5 + expand))
        mask = np.zeros((h, w), dtype=np.float32)
        cv2.ellipse(mask, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        return mask

    def _add_wrinkles(self, image: np.ndarray, intensity: float, face_mask):
        """增加皺紋效果"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edges = np.sqrt(sobelx**2 + sobely**2)
        edges = np.clip(edges, 0, 255).astype(np.uint8)
        wrinkle_mask = cv2.GaussianBlur(edges, (5, 5), 0).astype(np.float32) / 255.0
        if face_mask is not None:
            wrinkle_mask = wrinkle_mask * face_mask
        result = image.astype(np.float32)
        for i in range(3):
            result[:, :, i] = result[:, :, i] * (1 - wrinkle_mask * intensity * 0.5)
        return np.clip(result, 0, 255).astype(np.uint8)

    def _simulate_skin_aging(self, image: np.ndarray, age_factor: float, face_mask):
        """模擬皮膚老化"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
        saturation_factor = max(0.5, 1 - age_factor * 0.4)
        value_factor = 1 - age_factor * 0.1
        if face_mask is not None:
            face_mask_3d = face_mask[:, :, np.newaxis]
            hsv_aged = hsv.copy()
            hsv_aged[:, :, 1] = hsv[:, :, 1] * saturation_factor
            hsv_aged[:, :, 2] = hsv[:, :, 2] * value_factor
            hsv = hsv * (1 - face_mask_3d) + hsv_aged * face_mask_3d
        else:
            hsv[:, :, 1] = hsv[:, :, 1] * saturation_factor
            hsv[:, :, 2] = hsv[:, :, 2] * value_factor
        hsv = np.clip(hsv, 0, 255).astype(np.uint8)
        return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    def _add_hair_graying(self, image: np.ndarray, gray_ratio: float, face_rect):
        """模擬頭髮變白"""
        if face_rect is None:
            return image
        h, w = image.shape[:2]
        x, y, fw, fh = face_rect
        hair_top = max(0, y - int(fh * 0.8))
        hair_bottom = y + int(fh * 0.3)
        hair_left = max(0, x - int(fw * 0.3))
        hair_right = min(w, x + fw + int(fw * 0.3))
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hair_region = image[hair_top:hair_bottom, hair_left:hair_right].copy()
        hair_hsv = hsv[hair_top:hair_bottom, hair_left:hair_right]
        if hair_region.size == 0:
            return image
        lower_hair = np.array([0, 0, 0])
        upper_hair = np.array([180, 255, 80])
        hair_mask = cv2.inRange(hair_hsv, lower_hair, upper_hair)
        kernel = np.ones((5, 5), np.uint8)
        hair_mask = cv2.morphologyEx(hair_mask, cv2.MORPH_CLOSE, kernel)
        hair_mask = cv2.dilate(hair_mask, kernel, iterations=1)
        hair_mask = cv2.GaussianBlur(hair_mask, (15, 15), 0)
        gray_hair = cv2.cvtColor(hair_region, cv2.COLOR_BGR2GRAY)
        gray_hair = cv2.cvtColor(gray_hair, cv2.COLOR_GRAY2BGR)
        gray_hair = cv2.convertScaleAbs(gray_hair, alpha=1.2, beta=50)
        hair_mask_3ch = cv2.merge([hair_mask, hair_mask, hair_mask]).astype(np.float32) / 255.0
        blended = (hair_region.astype(np.float32) * (1 - hair_mask_3ch * gray_ratio) +
                   gray_hair.astype(np.float32) * hair_mask_3ch * gray_ratio)
        result = image.copy()
        result[hair_top:hair_bottom, hair_left:hair_right] = np.clip(blended, 0, 255).astype(np.uint8)
        return result

    def process(
        self,
        image_path: Union[str, Path],
        target_age: int = 75,
        initial_age: int = 25,
        gender: str = "male",
        output_filename: Optional[str] = None
    ) -> Optional[Path]:
        """使用 Mock 模式處理變老"""
        image_path = Path(image_path)
        if not image_path.exists():
            print(f"影像不存在: {image_path}")
            return None

        image = cv2.imread(str(image_path))
        if image is None:
            print(f"無法讀取影像: {image_path}")
            return None

        # 計算老化係數
        age_diff = max(0, target_age - initial_age)
        age_factor = min(1.0, age_diff / 60)

        print(f"[Mock] 模擬變老效果")
        print(f"   目標年齡: {target_age}, 老化係數: {age_factor:.2f}")

        # 偵測人臉
        face_rect = self._detect_face(image)
        if face_rect is None:
            print("   未偵測到人臉，跳過變老處理")
            aged = image
        else:
            print(f"   偵測到人臉: x={face_rect[0]}, y={face_rect[1]}")
            face_mask = self._create_face_mask(image, face_rect, expand=0.3)

            aged = image.copy()
            aged = self._simulate_skin_aging(aged, age_factor, face_mask)
            aged = self._add_wrinkles(aged, age_factor * 0.4, face_mask)
            if age_factor > 0.2:
                aged = self._add_hair_graying(aged, min(0.8, age_factor * 0.9), face_rect)

        # 儲存結果
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"aged_{target_age}_{timestamp}.jpg"

        output_path = AGED_DIR / output_filename
        cv2.imwrite(str(output_path), aged)
        print(f"   結果已儲存: {output_path}")

        return output_path


def age_photo(
    image_path: Union[str, Path],
    target_age: int = 75,
    engine: str = None,
    initial_age: int = 25,
    gender: str = "male",
    mock: Optional[bool] = None
) -> Optional[Path]:
    """快速將照片變老

    Args:
        image_path: 輸入影像路徑
        target_age: 目標年齡
        engine: 引擎選擇 ("fading", "mock")，None 使用設定檔預設
        initial_age: 估計的原始年齡
        gender: 性別 ("male" 或 "female")
        mock: True=強制 Mock 模式 (已棄用，請使用 engine="mock")

    Returns:
        輸出影像路徑
    """
    # 決定使用的引擎
    if mock:
        engine = "mock"
    elif engine is None:
        engine = AGING_ENGINE

    print(f"使用引擎: {engine}")

    if engine == "fading":
        processor = FADINGProcessor()
        return processor.process(image_path, target_age, initial_age, gender)
    else:
        processor = MockProcessor()
        return processor.process(image_path, target_age, initial_age, gender)


def age_photo_fading(
    image_path: Union[str, Path],
    target_ages: List[int] = None,
    initial_age: int = 25,
    gender: str = "male"
) -> List[Path]:
    """使用 FADING 處理多個目標年齡

    Args:
        image_path: 輸入影像路徑
        target_ages: 目標年齡列表
        initial_age: 估計的原始年齡
        gender: 性別 ("male" 或 "female")

    Returns:
        輸出影像路徑列表
    """
    processor = FADINGProcessor()
    return processor.process_multiple_ages(image_path, target_ages, initial_age, gender)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE 人臉變老處理")
    parser.add_argument("image", help="輸入影像路徑")
    parser.add_argument("--age", type=int, default=75, help="目標年齡（預設 75）")
    parser.add_argument("--engine", type=str, choices=["fading", "mock"],
                        default=None, help="引擎選擇（預設: fading）")
    parser.add_argument("--initial-age", type=int, default=25,
                        help="估計的原始年齡（預設 25）")
    parser.add_argument("--gender", type=str, choices=["male", "female"],
                        default="male", help="性別（預設 male）")
    parser.add_argument("--multi-age", action="store_true",
                        help="使用 FADING 處理多個年齡 (10, 20, 40, 60, 80)")

    args = parser.parse_args()

    if args.multi_age:
        results = age_photo_fading(
            args.image,
            target_ages=None,
            initial_age=args.initial_age,
            gender=args.gender
        )
        if results:
            print(f"\n處理完成，共 {len(results)} 張:")
            for r in results:
                print(f"   {r}")
        else:
            print("\n處理失敗")
    else:
        result = age_photo(
            args.image,
            args.age,
            engine=args.engine,
            initial_age=args.initial_age,
            gender=args.gender
        )

        if result:
            print(f"\n處理完成: {result}")
        else:
            print("\n處理失敗")
