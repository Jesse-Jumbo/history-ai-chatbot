"""
攝影機模組 - 負責拍照功能
支援即時預覽、倒數計時拍照、鏡像顯示
"""
import cv2
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAPTURED_DIR
)

# UI 顏色定義 (BGR)
COLOR_PRIMARY = (255, 200, 100)    # 淺藍色
COLOR_SUCCESS = (100, 255, 100)    # 綠色
COLOR_WARNING = (100, 200, 255)    # 橘黃色
COLOR_COUNTDOWN = (100, 100, 255)  # 紅色
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_OVERLAY = (50, 50, 50)


class Camera:
    """攝影機控制類別"""
    
    def __init__(self, camera_index: int = CAMERA_INDEX):
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_opened = False
    
    def open(self) -> bool:
        """開啟攝影機"""
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            print(f"❌ 無法開啟攝影機 {self.camera_index}")
            return False
        
        # 設定解析度
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        
        self.is_opened = True
        print(f"✅ 攝影機已開啟 (index: {self.camera_index})")
        return True
    
    def close(self):
        """關閉攝影機"""
        if self.cap:
            self.cap.release()
            self.is_opened = False
            print("📷 攝影機已關閉")
    
    def read_frame(self) -> Optional[cv2.typing.MatLike]:
        """讀取一幀畫面"""
        if not self.cap or not self.is_opened:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def capture_photo(self, filename: Optional[str] = None) -> Optional[Path]:
        """
        拍攝照片並儲存
        
        Args:
            filename: 自訂檔名，若無則自動生成
            
        Returns:
            儲存的檔案路徑，失敗則返回 None
        """
        frame = self.read_frame()
        if frame is None:
            print("❌ 無法讀取畫面")
            return None
        
        # 生成檔名
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.jpg"
        
        # 儲存路徑
        save_path = CAPTURED_DIR / filename
        
        # 儲存照片
        success = cv2.imwrite(str(save_path), frame)
        
        if success:
            print(f"📸 照片已儲存: {save_path}")
            return save_path
        else:
            print("❌ 儲存照片失敗")
            return None
    
    def _draw_ui_overlay(self, frame, message: str, sub_message: str = "",
                          show_guide: bool = True, mirror: bool = True):
        """繪製 UI 覆蓋層"""
        display = frame.copy()

        # 鏡像翻轉（讓使用者看到的是鏡像）
        if mirror:
            display = cv2.flip(display, 1)

        h, w = display.shape[:2]

        # 頂部半透明狀態列
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (w, 60), COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)

        # 主要訊息
        cv2.putText(display, message, (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLOR_PRIMARY, 2)

        # 底部操作提示
        if sub_message:
            overlay = display.copy()
            cv2.rectangle(overlay, (0, h-50), (w, h), COLOR_BLACK, -1)
            cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
            cv2.putText(display, sub_message, (20, h-18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 1)

        # 人臉引導框
        if show_guide:
            center_x, center_y = w // 2, h // 2
            guide_w, guide_h = int(w * 0.35), int(h * 0.55)

            # 橢圓形引導框
            cv2.ellipse(display, (center_x, center_y), (guide_w // 2, guide_h // 2),
                       0, 0, 360, COLOR_PRIMARY, 2)

            # 四角標記
            corner_len = 30
            corners = [
                (center_x - guide_w//2, center_y - guide_h//2),  # 左上
                (center_x + guide_w//2, center_y - guide_h//2),  # 右上
                (center_x - guide_w//2, center_y + guide_h//2),  # 左下
                (center_x + guide_w//2, center_y + guide_h//2),  # 右下
            ]
            for i, (cx, cy) in enumerate(corners):
                dx = corner_len if i % 2 == 0 else -corner_len
                dy = corner_len if i < 2 else -corner_len
                cv2.line(display, (cx, cy), (cx + dx, cy), COLOR_PRIMARY, 2)
                cv2.line(display, (cx, cy), (cx, cy + dy), COLOR_PRIMARY, 2)

        return display

    def _draw_countdown(self, frame, count: int, mirror: bool = True):
        """繪製倒數計時畫面"""
        display = frame.copy()
        if mirror:
            display = cv2.flip(display, 1)

        h, w = display.shape[:2]

        # 半透明覆蓋
        overlay = display.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), COLOR_BLACK, -1)
        cv2.addWeighted(overlay, 0.3, display, 0.7, 0, display)

        # 大型倒數數字
        text = str(count)
        font_scale = 8
        thickness = 15
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,
                                               font_scale, thickness)
        x = (w - text_w) // 2
        y = (h + text_h) // 2

        # 描邊效果
        cv2.putText(display, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, COLOR_BLACK, thickness + 5)
        cv2.putText(display, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, COLOR_COUNTDOWN, thickness)

        return display

    def _draw_flash(self, frame):
        """繪製拍照閃光效果"""
        h, w = frame.shape[:2]
        flash = frame.copy()
        cv2.rectangle(flash, (0, 0), (w, h), COLOR_WHITE, -1)
        cv2.addWeighted(flash, 0.7, frame, 0.3, 0, flash)
        return flash

    def preview_loop(self, window_name: str = "SAGE Camera",
                     countdown_seconds: int = 3,
                     mirror: bool = True) -> Optional[Path]:
        """
        預覽畫面，支援倒數計時拍照

        Args:
            window_name: 視窗名稱
            countdown_seconds: 倒數秒數（0 表示直接拍照）
            mirror: 是否鏡像顯示

        Returns:
            拍攝的照片路徑，若取消則返回 None

        Controls:
            空白鍵: 開始倒數拍照
            C: 直接拍照（不倒數）
            M: 切換鏡像
            ESC: 取消
        """
        if not self.is_opened:
            if not self.open():
                return None

        print("\n📷 攝影機預覽中...")
        print("   [空白鍵] 倒數拍照")
        print("   [C] 直接拍照")
        print("   [M] 切換鏡像")
        print("   [ESC] 取消\n")

        captured_path = None
        countdown_active = False
        countdown_start = 0
        current_count = 0

        while True:
            frame = self.read_frame()
            if frame is None:
                break

            current_time = time.time()

            # 倒數計時中
            if countdown_active:
                elapsed = current_time - countdown_start
                remaining = countdown_seconds - int(elapsed)

                if remaining <= 0:
                    # 閃光效果
                    flash_frame = self._draw_flash(frame)
                    cv2.imshow(window_name, flash_frame)
                    cv2.waitKey(100)

                    # 拍照（使用原始未鏡像的畫面）
                    captured_path = self.capture_photo()
                    break

                if remaining != current_count:
                    current_count = remaining
                    print(f"   ⏱️  {remaining}...")

                display = self._draw_countdown(frame, remaining, mirror)
            else:
                # 正常預覽
                display = self._draw_ui_overlay(
                    frame,
                    "SAGE Camera",
                    "[SPACE] Countdown  [C] Capture  [M] Mirror  [ESC] Cancel",
                    show_guide=True,
                    mirror=mirror
                )

            cv2.imshow(window_name, display)
            key = cv2.waitKey(1) & 0xFF

            if key == 32 and not countdown_active:  # 空白鍵 - 開始倒數
                countdown_active = True
                countdown_start = current_time
                current_count = countdown_seconds
                print(f"\n📸 倒數 {countdown_seconds} 秒拍照...")
            elif key == ord('c') or key == ord('C'):  # C - 直接拍照
                flash_frame = self._draw_flash(frame)
                cv2.imshow(window_name, flash_frame)
                cv2.waitKey(100)
                captured_path = self.capture_photo()
                break
            elif key == ord('m') or key == ord('M'):  # M - 切換鏡像
                mirror = not mirror
                mode = "開啟" if mirror else "關閉"
                print(f"   🔄 鏡像模式: {mode}")
            elif key == 27:  # ESC
                print("🚫 取消拍照")
                break

        cv2.destroyAllWindows()
        return captured_path
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def quick_capture() -> Optional[Path]:
    """快速拍攝一張照片"""
    with Camera() as cam:
        return cam.preview_loop()


if __name__ == "__main__":
    # 測試攝影機
    photo_path = quick_capture()
    if photo_path:
        print(f"\n✅ 測試完成，照片位置: {photo_path}")
    else:
        print("\n❌ 測試失敗或已取消")
