"""PoseExtractor: Orchestrates complete video analysis pipeline (video → poses → storage)."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .pose_detector import PoseDetector
from .skeleton_storage import SkeletonFrame, SkeletonStorage
from .video_extractor import VideoExtractor

logger = logging.getLogger(__name__)


class PoseExtractor:
    """Orchestrates video frame extraction, pose detection, and skeleton storage."""

    def analyze_video(
        self,
        video_path: str,
        output_dir: str,
        pose_name: str,
        skip_frames: int = 1,
    ) -> Dict[str, Any]:
        """Analyze video and extract pose landmarks, storing results.

        Pipeline:
        1. Initialize VideoExtractor for frame iteration
        2. Initialize PoseDetector for landmark extraction
        3. Initialize SkeletonStorage for pose persistence
        4. Iterate video frames, detect poses, store successful detections
        5. Return summary statistics

        Args:
            video_path: Path to input video file.
            output_dir: Directory for output storage files.
            pose_name: Name for the pose sequence (used as storage prefix).
            skip_frames: Process every Nth frame (default 1 = all frames).

        Returns:
            Dict with keys:
                - success (bool): Whether analysis completed without critical errors
                - total_frames (int): Total frames processed
                - detected_frames (int): Frames with successful pose detection
                - detection_rate (float): Ratio of detected_frames / total_frames
                - storage_path (str): Path to output storage directory
                - pose_name (str): Pose name used
                - error (str): Error message if success=False
        """
        total_frames = 0
        detected_frames = 0
        detector = None
        extractor = None
        storage = None

        try:
            extractor = VideoExtractor(video_path)
            logger.info(f"VideoExtractor created: {extractor.total_frames} frames, {extractor.fps} FPS")

            detector = PoseDetector(static_image_mode=False)
            logger.info("PoseDetector initialized")

            output_path = Path(output_dir)
            storage = SkeletonStorage(
                base_path=output_path,
                name=pose_name,
                mode="w",
                fps=extractor.fps,
            )
            logger.info(f"SkeletonStorage created at {output_path}")

            for frame_id, (frame, timestamp) in enumerate(extractor.iterate_frames()):
                if frame_id % skip_frames != 0:
                    continue

                total_frames += 1

                if total_frames % 30 == 0:
                    logger.info(f"Processing frame {total_frames}/{extractor.total_frames}")

                pose_result = detector.process_frame(frame)

                if pose_result and pose_result.get("body_landmarks") is not None:
                    body = np.array(pose_result["body_landmarks"], dtype=np.float32)
                    left_hand = np.array(pose_result.get("hand_landmarks_left") or [], dtype=np.float32)
                    right_hand = np.array(pose_result.get("hand_landmarks_right") or [], dtype=np.float32)
                    face = np.array(pose_result.get("face_landmarks") or [], dtype=np.float32)

                    skeleton_frame = SkeletonFrame(
                        frame_id=frame_id,
                        timestamp=timestamp,
                        body_pose=body,
                        left_hand=left_hand,
                        right_hand=right_hand,
                        face=face,
                        metadata={"pose_name": pose_name},
                    )
                    storage.add_frame(skeleton_frame)
                    detected_frames += 1

            storage.finalize()
            logger.info(f"Analysis complete: {detected_frames}/{total_frames} frames detected")

            detection_rate = detected_frames / total_frames if total_frames > 0 else 0.0

            return {
                "success": True,
                "total_frames": total_frames,
                "detected_frames": detected_frames,
                "detection_rate": detection_rate,
                "storage_path": str(output_path),
                "pose_name": pose_name,
            }

        except Exception as e:
            logger.error(f"Error during video analysis: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

        finally:
            if detector is not None:
                detector.close()
            if extractor is not None:
                extractor.close()
            if storage is not None:
                storage.close()
