"""
SAGE 模型下載工具
下載 FADING (Face Aging via Diffusion-based Editing) 所需的預訓練模型
https://github.com/gh-BumsooKim/FADING_stable
"""
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

# 加入專案路徑
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    MODELS_DIR,
    MODEL_PATHS,
    MODEL_URLS,
    FADING_MODEL_PATH,
)


def download_with_progress(url: str, dest: Path, desc: str = "Downloading") -> bool:
    """帶進度條的下載"""
    try:
        from tqdm import tqdm
        import urllib.request

        # 獲取檔案大小
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('content-length', 0))

        # 下載並顯示進度
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
            def reporthook(block_num, block_size, total_size):
                pbar.update(block_size)

            urllib.request.urlretrieve(url, str(dest), reporthook=reporthook)
        return True

    except ImportError:
        # 沒有 tqdm，使用普通下載
        print(f"   下載中: {url}")
        urllib.request.urlretrieve(url, str(dest))
        return True

    except Exception as e:
        print(f"   下載失敗: {e}")
        return False


def download_gdown(file_id: str, dest: Path, desc: str = "Downloading") -> bool:
    """使用 gdown 從 Google Drive 下載"""
    try:
        import gdown
        print(f"   使用 gdown 下載: {desc}")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(dest), quiet=False)
        return dest.exists()
    except Exception as e:
        print(f"   gdown 下載失敗: {e}")
        return False


def download_fading_model() -> bool:
    """下載 FADING 擴散模型"""
    model_path = FADING_MODEL_PATH

    if model_path.exists() and (model_path / "model_index.json").exists():
        print(f"   FADING 模型已存在: {model_path}")
        return True

    print(f"   下載 FADING 擴散模型...")
    print("   這是一個大型模型 (~4.5 GB)，請耐心等待...")

    # FADING 模型 Google Drive ID
    # From: https://github.com/gh-BumsooKim/FADING_stable
    file_id = "1galwrcHq1HoZNfOI4jdJJqVs5ehB_dvO"
    zip_path = MODELS_DIR / "finetune_double_prompt_150_random.zip"

    try:
        import gdown
        print(f"   從 Google Drive 下載...")
        gdown.download(id=file_id, output=str(zip_path), quiet=False)

        if not zip_path.exists():
            print(f"   下載失敗: 找不到 zip 檔案")
            return False

        # 解壓縮
        print(f"   解壓縮中...")
        import zipfile
        with zipfile.ZipFile(str(zip_path), 'r') as zip_ref:
            zip_ref.extractall(str(MODELS_DIR))

        # 刪除 zip 檔案
        zip_path.unlink()
        print(f"   FADING 模型下載完成: {model_path}")
        return True

    except ImportError:
        print(f"   需要安裝 gdown: pip install gdown")
        print(f"   或手動下載:")
        print(f"   1. 前往: https://drive.google.com/file/d/{file_id}")
        print(f"   2. 下載並解壓縮到: {MODELS_DIR}")
        return False

    except Exception as e:
        print(f"   下載失敗: {e}")
        return False


def download_mediapipe_landmarker() -> bool:
    """下載 MediaPipe Face Landmarker 模型"""
    landmarker_path = MODEL_PATHS["mediapipe_landmarker"]

    if landmarker_path.exists():
        size_mb = landmarker_path.stat().st_size / (1024 * 1024)
        print(f"   模型已存在: {landmarker_path} ({size_mb:.1f} MB)")
        return True

    print(f"   下載 MediaPipe Face Landmarker 模型...")
    landmarker_path.parent.mkdir(parents=True, exist_ok=True)

    success = download_with_progress(
        MODEL_URLS["mediapipe_landmarker"],
        landmarker_path,
        "face_landmarker.task"
    )

    if success and landmarker_path.exists():
        size_mb = landmarker_path.stat().st_size / (1024 * 1024)
        print(f"   模型已下載: {landmarker_path} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"   下載失敗")
        return False


def verify_models() -> dict:
    """驗證所有模型檔案"""
    results = {}

    print("\n模型驗證")
    print("-" * 50)

    # 檢查 FADING 模型
    if FADING_MODEL_PATH.exists() and (FADING_MODEL_PATH / "model_index.json").exists():
        results["fading"] = {"exists": True}
        print(f"   FADING: {FADING_MODEL_PATH.name}")
    else:
        results["fading"] = {"exists": False}
        print(f"   FADING: 未找到")

    # 檢查 MediaPipe
    mp_path = MODEL_PATHS["mediapipe_landmarker"]
    if mp_path.exists():
        size_mb = mp_path.stat().st_size / (1024 * 1024)
        results["mediapipe"] = {"exists": True, "size_mb": size_mb}
        print(f"   MediaPipe: {mp_path.name} ({size_mb:.1f} MB)")
    else:
        results["mediapipe"] = {"exists": False, "size_mb": 0}
        print(f"   MediaPipe: 未找到")

    return results


def check_dependencies():
    """檢查下載所需的依賴"""
    print("\n檢查依賴套件")
    print("-" * 50)

    dependencies = {
        "gdown": "用於從 Google Drive 下載",
        "tqdm": "用於顯示下載進度",
        "diffusers": "用於載入 FADING 模型",
        "transformers": "用於文字處理",
    }

    all_ok = True
    for pkg, desc in dependencies.items():
        try:
            __import__(pkg)
            print(f"   {pkg}: {desc}")
        except ImportError:
            print(f"   {pkg}: 未安裝 ({desc})")
            all_ok = False

    if not all_ok:
        print("\n   提示: 執行 'pip install gdown tqdm diffusers transformers' 安裝缺失套件")

    return all_ok


def main():
    """下載所有必要模型"""
    print("\n" + "=" * 60)
    print("SAGE 模型下載工具")
    print("   基於 FADING (Face Aging via Diffusion-based Editing)")
    print("   https://github.com/gh-BumsooKim/FADING_stable")
    print("=" * 60)

    # 確保目錄存在
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 檢查依賴
    if not check_dependencies():
        print("\n請先安裝缺失的依賴套件")

    results = []

    # ===== FADING 核心模型 =====
    print("\n" + "=" * 60)
    print("FADING 核心模型")
    print("=" * 60)

    # 1. FADING 擴散模型 (必需)
    print("\n[1/2] FADING 擴散模型 (~4.5 GB)")
    results.append(("FADING", download_fading_model()))

    # 2. MediaPipe Face Landmarker (可選，用於人臉偵測)
    print("\n[2/2] MediaPipe Face Landmarker")
    results.append(("MediaPipe", download_mediapipe_landmarker()))

    # 驗證結果
    verify_models()

    # 總結
    print("\n" + "=" * 60)
    success_count = sum(1 for _, success in results if success)
    total = len(results)

    if success_count == total:
        print("所有模型下載完成！")
    elif success_count > 0:
        print(f"部分模型下載完成 ({success_count}/{total})")
    else:
        print("模型下載失敗")

    print("=" * 60)

    # 顯示下一步
    print("\n下一步:")
    print("   1. 執行 'python src/main.py --status' 檢查系統狀態")
    print("   2. 執行 'python src/main.py --gpu' 使用 GPU 模式")
    print("   3. 執行 'python src/main.py --mock' 使用模擬模式（開發用）\n")


if __name__ == "__main__":
    main()
