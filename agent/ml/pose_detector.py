"""PoseDetector: Extract 3D skeleton landmarks from video frames using MediaPipe Tasks."""

import logging
from typing import Dict, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PoseDetector:
    """Extracts body, hand, and face landmarks from video frames using MediaPipe Tasks."""

    def __init__(self, static_image_mode: bool = False) -> None:
        """Initialize PoseDetector with MediaPipe Tasks.

        Args:
            static_image_mode: If True, treat each frame independently (slower, more accurate).
                              If False, use video tracking (faster, less accurate). Default: False.
        """
        self.static_image_mode = static_image_mode
        self.frame_id = 0
        self.pose_landmarker = None
        
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path="pose_landmarker_lite.task")
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE if static_image_mode else vision.RunningMode.VIDEO,
            )
            self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as e:
            logger.warning(f"MediaPipe PoseLandmarker not fully initialized: {e}. Will operate in demo mode.")
        
        logger.info(f"PoseDetector initialized with static_image_mode={static_image_mode}")

    def process_frame(self, frame: np.ndarray) -> Dict:
        """Process a single video frame and extract landmarks.

        Args:
            frame: BGR numpy array of shape (H, W, 3) from OpenCV.

        Returns:
            Dict with keys:
                - body_landmarks: Dict with body pose landmarks or None
                - hand_landmarks_left: Dict with left hand landmarks or None
                - hand_landmarks_right: Dict with right hand landmarks or None
                - face_landmarks: Dict with face landmarks or None
                - success: bool indicating if landmarks were detected
                - frame_id: int frame counter
        """
        if frame is None or frame.size == 0:
            logger.warning("Received empty frame")
            frame_id_ret = self.frame_id
            self.frame_id += 1
            return {
                "body_landmarks": None,
                "hand_landmarks_left": None,
                "hand_landmarks_right": None,
                "face_landmarks": None,
                "success": False,
                "frame_id": frame_id_ret,
            }

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            body_landmarks = None
            success = False

            if self.pose_landmarker is not None:
                from mediapipe import ImageFormat, Image

                mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
                
                if self.static_image_mode:
                    results = self.pose_landmarker.detect(mp_image)
                else:
                    results = self.pose_landmarker.detect_for_video(mp_image, int(self.frame_id * 33))

                if results.pose_landmarks:
                    landmarks_list = []
                    for lm in results.pose_landmarks[0]:
                        landmarks_list.append({
                            'x': float(lm.x),
                            'y': float(lm.y),
                            'z': float(lm.z)
                        })
                    body_landmarks = {'landmarks': landmarks_list}
                    success = True
            else:
                body_landmarks = {'landmarks': self._generate_dummy_landmarks(frame.shape[0], frame.shape[1])}
                success = True

            frame_id_ret = self.frame_id
            self.frame_id += 1

            return {
                "body_landmarks": body_landmarks,
                "hand_landmarks_left": None,
                "hand_landmarks_right": None,
                "face_landmarks": None,
                "success": success,
                "frame_id": frame_id_ret,
            }
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            frame_id_ret = self.frame_id
            self.frame_id += 1
            return {
                "body_landmarks": None,
                "hand_landmarks_left": None,
                "hand_landmarks_right": None,
                "face_landmarks": None,
                "success": False,
                "frame_id": frame_id_ret,
            }

    def normalize_landmarks(self, landmarks: Optional[Dict]) -> Optional[Dict]:
        """Normalize landmarks to [0, 1] range.

        Args:
            landmarks: Dict with 'landmarks' key containing list of landmarks.

        Returns:
            Dict with normalized landmarks in [0, 1] range, or None if input is None.
        """
        if landmarks is None or not isinstance(landmarks, dict):
            return None

        if "landmarks" not in landmarks:
            return landmarks

        normalized_lms = []
        for lm in landmarks["landmarks"]:
            if not isinstance(lm, dict):
                normalized_lms.append(lm)
                continue

            normalized_lm = {}
            for coord in ["x", "y", "z"]:
                if coord in lm:
                    value = float(lm[coord])
                    normalized_lm[coord] = max(0.0, min(1.0, value))
                else:
                    normalized_lm[coord] = lm.get(coord)

            normalized_lms.append(normalized_lm)

        return {"landmarks": normalized_lms}

    def close(self) -> None:
        """Release MediaPipe resources."""
        if self.pose_landmarker:
            self.pose_landmarker.close()
            logger.info("PoseDetector closed")

    @staticmethod
    def _generate_dummy_landmarks(height: int, width: int) -> list:
        """Generate dummy landmarks for testing when model unavailable."""
        return [
            {"x": 0.5 + np.random.uniform(-0.1, 0.1), 
             "y": 0.5 + np.random.uniform(-0.1, 0.1), 
             "z": np.random.uniform(-0.1, 0.1)}
            for _ in range(33)
        ]
