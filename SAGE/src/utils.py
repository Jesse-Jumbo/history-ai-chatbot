"""
工具函數
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional


def resize_image(image: np.ndarray, target_size: int = 1024, keep_aspect: bool = True) -> np.ndarray:
    """調整影像大小"""
    h, w = image.shape[:2]
    
    if keep_aspect:
        if h > w:
            new_h = target_size
            new_w = int(w * target_size / h)
        else:
            new_w = target_size
            new_h = int(h * target_size / w)
    else:
        new_w = new_h = target_size
    
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def center_crop(image: np.ndarray, size: int) -> np.ndarray:
    """中心裁切"""
    h, w = image.shape[:2]
    start_x = max(0, (w - size) // 2)
    start_y = max(0, (h - size) // 2)
    return image[start_y:start_y+size, start_x:start_x+size]


def detect_face(image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """偵測人臉位置"""
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    
    if len(faces) == 0:
        return None
    
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    return tuple(faces[0])


def crop_face(image: np.ndarray, padding: float = 0.3) -> Optional[np.ndarray]:
    """偵測並裁切人臉區域"""
    face = detect_face(image)
    if face is None:
        return None
    
    x, y, w, h = face
    pad_w = int(w * padding)
    pad_h = int(h * padding)
    
    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(image.shape[1], x + w + pad_w)
    y2 = min(image.shape[0], y + h + pad_h)
    
    return image[y1:y2, x1:x2]


def show_comparison(original: np.ndarray, aged: np.ndarray, window_name: str = "SAGE Comparison"):
    """並排顯示原圖和變老結果"""
    h1, w1 = original.shape[:2]
    h2, w2 = aged.shape[:2]
    max_h = max(h1, h2)
    
    if h1 != max_h:
        scale = max_h / h1
        original = cv2.resize(original, None, fx=scale, fy=scale)
    if h2 != max_h:
        scale = max_h / h2
        aged = cv2.resize(aged, None, fx=scale, fy=scale)
    
    cv2.putText(original, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(aged, "Aged", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    comparison = np.hstack([original, aged])
    cv2.imshow(window_name, comparison)
    print("\n按任意鍵關閉視窗...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
