"""
Face alignment utilities using MediaPipe Tasks API
用於人臉對齊和特徵點偵測
"""
import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path
import urllib.request


# Standard face landmarks for alignment (based on FFHQ alignment)
FFHQ_LANDMARKS = np.array([
    [38.2946, 51.6963],   # Left eye
    [73.5318, 51.5014],   # Right eye
    [56.0252, 71.7366],   # Nose
    [41.5493, 92.3655],   # Left mouth
    [70.7299, 92.2041]    # Right mouth
], dtype=np.float32)


class FaceAligner:
    """Face alignment using MediaPipe Tasks API (0.10.30+)"""

    def __init__(self):
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        # Download model if not exists
        model_path = Path(__file__).parent.parent.parent / "models" / "face_landmarker.task"
        if not model_path.exists():
            print("Downloading Face Landmarker model...")
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            model_path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(model_path))
            print(f"Model downloaded: {model_path}")

        # Create FaceLandmarker
        base_options = python.BaseOptions(model_asset_path=str(model_path))
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

        # MediaPipe landmark indices for key points
        self.left_eye_indices = [33, 133, 160, 159, 158, 144, 145, 153]
        self.right_eye_indices = [362, 263, 387, 386, 385, 373, 374, 380]
        self.nose_index = 1
        self.left_mouth_index = 61
        self.right_mouth_index = 291

    def get_landmarks(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Extract 5-point landmarks from face"""
        import mediapipe as mp

        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

        # Detect face landmarks
        results = self.detector.detect(mp_image)

        if not results.face_landmarks:
            return None

        h, w = image.shape[:2]
        landmarks = results.face_landmarks[0]

        # Calculate key points
        def get_point(indices):
            if isinstance(indices, list):
                x = np.mean([landmarks[i].x for i in indices])
                y = np.mean([landmarks[i].y for i in indices])
            else:
                x = landmarks[indices].x
                y = landmarks[indices].y
            return [x * w, y * h]

        points = np.array([
            get_point(self.left_eye_indices),    # Left eye
            get_point(self.right_eye_indices),   # Right eye
            get_point(self.nose_index),          # Nose
            get_point(self.left_mouth_index),    # Left mouth
            get_point(self.right_mouth_index),   # Right mouth
        ], dtype=np.float32)

        return points

    def align_face(self, image: np.ndarray, output_size: int = 256,
                   transform_size: int = 1024) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Align face similar to FFHQ alignment

        Args:
            image: Input BGR image
            output_size: Output image size
            transform_size: Internal transform size

        Returns:
            Aligned face image and transformation matrix
        """
        landmarks = self.get_landmarks(image)
        if landmarks is None:
            return None, None

        # Scale FFHQ landmarks to output size
        scale = output_size / 112.0
        dst_landmarks = FFHQ_LANDMARKS * scale

        # Estimate transformation matrix
        M = cv2.estimateAffinePartial2D(landmarks, dst_landmarks)[0]

        if M is None:
            return None, None

        # Apply transformation
        aligned = cv2.warpAffine(image, M, (output_size, output_size),
                                  borderMode=cv2.BORDER_REPLICATE)

        return aligned, M

    def inverse_align(self, aligned_face: np.ndarray, M: np.ndarray,
                      original_size: Tuple[int, int]) -> np.ndarray:
        """
        Apply inverse transformation to put aligned face back

        Args:
            aligned_face: Aligned face image
            M: Original transformation matrix
            original_size: (width, height) of original image

        Returns:
            Face in original image space
        """
        # Invert the transformation matrix
        M_inv = cv2.invertAffineTransform(M)

        # Apply inverse transformation
        result = cv2.warpAffine(aligned_face, M_inv, original_size,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))

        return result

    def close(self):
        """Release resources"""
        self.detector.close()
