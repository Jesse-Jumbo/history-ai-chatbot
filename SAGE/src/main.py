"""
SAGE - Self-Aging Generative Experience
主程式入口
"""
import argparse
import sys
from pathlib import Path

# 加入專案路徑
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import AUTO_MOCK, MOCK_MODE
from src.camera import Camera, quick_capture
from src.aging import age_photo


def print_banner():
    """列印程式標題"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║   ███████╗ █████╗  ██████╗ ███████╗                       ║
    ║   ██╔════╝██╔══██╗██╔════╝ ██╔════╝                       ║
    ║   ███████╗███████║██║  ███╗█████╗                         ║
    ║   ╚════██║██╔══██║██║   ██║██╔══╝                         ║
    ║   ███████║██║  ██║╚██████╔╝███████╗                       ║
    ║   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝                       ║
    ║                                                           ║
    ║   Self-Aging Generative Experience                        ║
    ║   與未來老年的自己對話                                      ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_capture_and_age(mock: bool = None, target_age: int = 75):
    """執行拍照並變老的完整流程"""
    print("\n" + "="*50)
    print("📷 Step 1: 拍照")
    print("="*50)

    # 拍照
    photo_path = quick_capture()

    if photo_path is None:
        print("\n❌ 拍照取消或失敗")
        return None, None

    print("\n" + "="*50)
    print("🧓 Step 2: 變老處理")
    print("="*50)

    # 變老處理
    aged_path = age_photo(photo_path, target_age, mock=mock)

    if aged_path is None:
        print("\n❌ 變老處理失敗")
        return photo_path, None

    print("\n" + "="*50)
    print("✅ 處理完成！")
    print("="*50)
    print(f"   原始照片: {photo_path}")
    print(f"   變老結果: {aged_path}")

    # 顯示對比圖
    try:
        import cv2
        from src.utils import show_comparison
        original = cv2.imread(str(photo_path))
        aged = cv2.imread(str(aged_path))
        if original is not None and aged is not None:
            show_comparison(original, aged)
    except Exception as e:
        print(f"   ⚠️  無法顯示對比圖: {e}")

    return photo_path, aged_path


def run_age_only(image_path: str, mock: bool = None, target_age: int = 75):
    """只執行變老處理（使用現有照片）"""
    print("\n" + "="*50)
    print("🧓 變老處理")
    print("="*50)
    
    aged_path = age_photo(image_path, target_age, mock=mock)
    
    if aged_path:
        print(f"\n✅ 處理完成: {aged_path}")
    else:
        print("\n❌ 處理失敗")
    
    return aged_path


def show_status():
    """顯示系統狀態"""
    print("\n📊 系統狀態")
    print("-" * 40)

    # CUDA 狀態（安全檢查，避免環境衝突）
    gpu_status = "❓ 未檢測"
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_status = f"✅ {gpu_name}"
        else:
            gpu_status = "❌ CUDA 不可用"
    except ImportError:
        gpu_status = "⚠️ PyTorch 未安裝"
    except Exception as e:
        gpu_status = f"⚠️ 檢測失敗 ({type(e).__name__})"

    print(f"   GPU: {gpu_status}")

    # 模式
    if MOCK_MODE:
        print("   模式: 🎭 Mock（環境變數設定）")
    elif AUTO_MOCK:
        print("   模式: 🎭 Mock（預設模式）")
    else:
        print("   模式: 🚀 正式模式")

    # 攝影機
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("   攝影機: ✅ 可用")
            cap.release()
        else:
            print("   攝影機: ❌ 無法開啟")
    except Exception as e:
        print(f"   攝影機: ❌ {e}")

    print("-" * 40)


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="SAGE - Self-Aging Generative Experience",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  python main.py                    # 拍照並變老（預設 Mock 模式）
  python main.py --gpu              # 使用 GPU 運行（需要 CUDA）
  python main.py --mock             # 強制使用模擬模式
  python main.py -i photo.jpg --gpu # 用 GPU 處理現有照片
  python main.py -i photo.jpg -a 80 # 指定目標年齡 80 歲
  python main.py --status           # 顯示系統狀態
        """
    )

    parser.add_argument("-i", "--input", type=str, help="輸入影像路徑")
    parser.add_argument("-a", "--age", type=int, default=75, help="目標年齡")
    parser.add_argument("--mock", action="store_true", help="強制模擬模式")
    parser.add_argument("--gpu", action="store_true", help="強制使用 GPU（需要 CUDA 和 FADING 模型）")
    parser.add_argument("--status", action="store_true", help="顯示系統狀態")

    args = parser.parse_args()

    # 列印標題
    print_banner()

    # 顯示狀態
    if args.status:
        show_status()
        return

    # 決定模式: --gpu → False, --mock → True, 否則 → None (自動)
    if args.gpu:
        use_mock = False  # 強制 GPU 模式
        mode_str = "🚀 GPU 模式"
        # 檢查 CUDA 是否可用
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                print(f"\n🖥️  GPU: {gpu_name}")
            else:
                print("\n⚠️  警告: CUDA 不可用，將嘗試使用 CPU 推理")
        except ImportError:
            print("\n⚠️  警告: PyTorch 未安裝，可能無法使用 GPU")
    elif args.mock:
        use_mock = True  # 強制 Mock 模式
        mode_str = "🎭 Mock 模式"
    else:
        use_mock = None  # 自動偵測
        mode_str = "🎭 Mock 模式" if AUTO_MOCK else "🚀 自動模式"
    print(f"\n運行模式: {mode_str}")

    # 執行
    if args.input:
        run_age_only(args.input, mock=use_mock, target_age=args.age)
    else:
        run_capture_and_age(mock=use_mock, target_age=args.age)


if __name__ == "__main__":
    main()
