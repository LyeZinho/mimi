"""KeyframeStorage: Efficient msgpack storage for pose keyframes.

Format v2 features vs legacy SkeletonStorage:
  - Stores only keyframes (not every frame) — 60-80% fewer entries
  - Landmarks stored as float16 instead of float32 — 50% size reduction
  - Body landmarks converted to quaternions before storage — VRM-ready
  - Face reduced to 6 essential landmarks (not 468)
  - Hands omitted when not detected
  - Catmull-Rom tangents pre-computed and stored for smooth playback
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import msgpack
import numpy as np

from .pose_smoother import compute_bezier_tangents

logger = logging.getLogger(__name__)

FORMAT_VERSION = 2

# 6 essential face landmarks out of 468:
# nose tip, chin, left eye, right eye, left mouth, right mouth
_FACE_KEY_INDICES = [1, 152, 33, 263, 61, 291]

# MediaPipe body landmark pairs used to derive bone quaternions
# Each tuple: (parent_joint_idx, child_joint_idx, vrm_bone_name)
_BONE_PAIRS: List[tuple] = [
    (11, 13, "leftUpperArm"),
    (13, 15, "leftLowerArm"),
    (12, 14, "rightUpperArm"),
    (14, 16, "rightLowerArm"),
    (23, 25, "leftUpperLeg"),
    (25, 27, "leftLowerLeg"),
    (24, 26, "rightUpperLeg"),
    (26, 28, "rightLowerLeg"),
    (11, 12, "chest"),
    (23, 24, "hips"),
    (11, 23, "spine"),
    (0, 11, "neck"),
    (0, 0, "head"),  # nose — identity quaternion placeholder
]


@dataclass
class KeyframeEntry:
    """A single stored keyframe with pre-computed bone quaternions."""

    frame_id: int
    timestamp: float
    frame_type: str  # "key" | "missing"
    # shape (N_bones, 4) float16 — quaternions xyzw per bone
    bones: np.ndarray
    # shape (6, 3) float16 or None
    face: Optional[np.ndarray] = None
    # shape (21, 3) float16 or None
    left_hand: Optional[np.ndarray] = None
    # shape (21, 3) float16 or None
    right_hand: Optional[np.ndarray] = None


class KeyframeStorage:
    """Stores and loads pose keyframe data in optimised msgpack format (v2).

    Write mode: accumulate keyframes, call finalize() to flush to disk.
    Read mode: load from disk on init, access via get_frame() or all_keyframes.
    """

    def __init__(
        self,
        base_path: Path,
        name: str,
        mode: str = "w",
        fps: float = 30.0,
    ) -> None:
        if mode not in ("r", "w"):
            raise ValueError(f"Invalid mode {mode!r}. Must be 'r' or 'w'.")

        self.base_path = Path(base_path)
        self.name = name
        self.mode = mode
        self.fps = fps

        self.base_path.mkdir(parents=True, exist_ok=True)

        self._keyframes: List[KeyframeEntry] = []
        self._header: Dict[str, Any] = {}

        if mode == "r":
            self._load()

        logger.info(f"KeyframeStorage({name!r}, mode={mode!r}, fps={fps})")

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def add_keyframe(
        self,
        frame_id: int,
        timestamp: float,
        landmarks: np.ndarray,
        frame_type: str = "key",
        left_hand: Optional[np.ndarray] = None,
        right_hand: Optional[np.ndarray] = None,
        face: Optional[np.ndarray] = None,
    ) -> None:
        """Add a validated, smoothed landmark frame as a keyframe entry.

        Args:
            frame_id: Original video frame index.
            timestamp: Frame timestamp in seconds.
            landmarks: shape (33, 3) float32 — body landmarks.
            frame_type: "key" or "missing".
            left_hand: shape (21, 3) or None.
            right_hand: shape (21, 3) or None.
            face: shape (468, 3) or None — will be reduced to 6 key points.
        """
        if self.mode != "w":
            raise ValueError("Cannot add keyframes in read mode.")

        bones = _landmarks_to_quaternions(landmarks)
        face_reduced = _reduce_face(face)
        left_f16 = _to_float16_or_none(left_hand)
        right_f16 = _to_float16_or_none(right_hand)

        entry = KeyframeEntry(
            frame_id=frame_id,
            timestamp=timestamp,
            frame_type=frame_type,
            bones=bones,
            face=face_reduced,
            left_hand=left_f16,
            right_hand=right_f16,
        )
        self._keyframes.append(entry)

    def add_missing_frame(self, frame_id: int, timestamp: float) -> None:
        """Record a frame where detection failed (no landmarks)."""
        if self.mode != "w":
            raise ValueError("Cannot add keyframes in read mode.")
        entry = KeyframeEntry(
            frame_id=frame_id,
            timestamp=timestamp,
            frame_type="missing",
            bones=np.zeros((len(_BONE_PAIRS), 4), dtype=np.float16),
        )
        self._keyframes.append(entry)

    def finalize(self) -> None:
        """Write all keyframes + tangents to disk (write mode only)."""
        if self.mode != "w":
            logger.warning("finalize() called in read mode, skipping.")
            return
        if not self._keyframes:
            logger.warning("finalize() called with zero keyframes.")
            return

        bone_arrays = [kf.bones for kf in self._keyframes]
        tangents = compute_bezier_tangents(bone_arrays)

        self._write_msgpack(tangents)
        self._write_metadata()
        logger.info(f"KeyframeStorage finalized: {len(self._keyframes)} keyframes")

    def close(self) -> None:
        logger.debug(f"KeyframeStorage({self.name!r}) closed.")

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    @property
    def total_keyframes(self) -> int:
        return len(self._keyframes)

    @property
    def all_keyframes(self) -> List[KeyframeEntry]:
        return list(self._keyframes)

    def get_frame(self, frame_id: int) -> Optional[KeyframeEntry]:
        """Return the keyframe entry with matching frame_id, or None."""
        for kf in self._keyframes:
            if kf.frame_id == frame_id:
                return kf
        return None

    def to_json_serializable(self) -> Dict[str, Any]:
        """Return the full keyframe set as a JSON-serialisable dict for the web preview."""
        kfs = []
        for kf in self._keyframes:
            entry: Dict[str, Any] = {
                "frame_id": kf.frame_id,
                "timestamp": float(kf.timestamp),
                "type": kf.frame_type,
                "bones": kf.bones.astype(np.float32).tolist(),
            }
            if kf.face is not None:
                entry["face"] = kf.face.astype(np.float32).tolist()
            if kf.left_hand is not None:
                entry["left_hand"] = kf.left_hand.astype(np.float32).tolist()
            if kf.right_hand is not None:
                entry["right_hand"] = kf.right_hand.astype(np.float32).tolist()
            kfs.append(entry)
        return {
            "format_version": FORMAT_VERSION,
            "fps": self.fps,
            "total_keyframes": len(self._keyframes),
            "bone_names": [bp[2] for bp in _BONE_PAIRS],
            "keyframes": kfs,
        }

    # ------------------------------------------------------------------
    # Private: write
    # ------------------------------------------------------------------

    def _write_msgpack(self, tangents: List[np.ndarray]) -> None:
        frames_list = []
        for i, kf in enumerate(self._keyframes):
            entry: Dict[str, Any] = {
                "frame_id": kf.frame_id,
                "timestamp": np.float16(kf.timestamp).item(),
                "type": kf.frame_type,
                "bones": kf.bones.tobytes(),
            }
            if kf.face is not None:
                entry["face"] = kf.face.tobytes()
            if kf.left_hand is not None:
                entry["left_hand"] = kf.left_hand.tobytes()
            if kf.right_hand is not None:
                entry["right_hand"] = kf.right_hand.tobytes()
            entry["tangent"] = tangents[i].tobytes()
            frames_list.append(entry)

        payload = {
            "format_version": FORMAT_VERSION,
            "fps": self.fps,
            "total_keyframes": len(frames_list),
            "bone_names": [bp[2] for bp in _BONE_PAIRS],
            "keyframes": frames_list,
        }
        out_path = self.base_path / f"{self.name}.keyframes.msgpack"
        with open(out_path, "wb") as f:
            f.write(msgpack.packb(payload, use_bin_type=True))
        logger.debug(f"Wrote {len(frames_list)} keyframes to {out_path}")

    def _write_metadata(self) -> None:
        duration = 0.0
        if self._keyframes:
            duration = self._keyframes[-1].timestamp - self._keyframes[0].timestamp
        meta = {
            "name": self.name,
            "format_version": FORMAT_VERSION,
            "fps": self.fps,
            "total_keyframes": len(self._keyframes),
            "duration_sec": duration,
            "bone_names": [bp[2] for bp in _BONE_PAIRS],
        }
        meta_path = self.base_path / f"{self.name}.keyframes_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    # ------------------------------------------------------------------
    # Private: read
    # ------------------------------------------------------------------

    def _load(self) -> None:
        msgpack_path = self.base_path / f"{self.name}.keyframes.msgpack"
        if not msgpack_path.exists():
            logger.warning(f"Keyframe file not found: {msgpack_path}")
            return

        with open(msgpack_path, "rb") as f:
            payload = msgpack.unpackb(f.read(), raw=False)

        self.fps = payload.get("fps", self.fps)
        n_bones = len(payload.get("bone_names", _BONE_PAIRS))

        for entry in payload.get("keyframes", []):
            bones = np.frombuffer(entry["bones"], dtype=np.float16).reshape(
                n_bones, 4
            )
            face = (
                np.frombuffer(entry["face"], dtype=np.float16).reshape(6, 3)
                if "face" in entry
                else None
            )
            left_hand = (
                np.frombuffer(entry["left_hand"], dtype=np.float16).reshape(21, 3)
                if "left_hand" in entry
                else None
            )
            right_hand = (
                np.frombuffer(entry["right_hand"], dtype=np.float16).reshape(21, 3)
                if "right_hand" in entry
                else None
            )
            kf = KeyframeEntry(
                frame_id=entry["frame_id"],
                timestamp=float(entry["timestamp"]),
                frame_type=entry.get("type", "key"),
                bones=bones,
                face=face,
                left_hand=left_hand,
                right_hand=right_hand,
            )
            self._keyframes.append(kf)

        logger.info(f"Loaded {len(self._keyframes)} keyframes from {msgpack_path}")


# ------------------------------------------------------------------
# Conversion helpers
# ------------------------------------------------------------------

def _landmarks_to_quaternions(landmarks: np.ndarray) -> np.ndarray:
    """Convert MediaPipe body landmarks (33, 3) to bone quaternions (N_bones, 4) float16.

    Each bone quaternion is derived from the direction vector between its
    parent and child joints, rotated relative to the canonical up-axis (0, 1, 0).
    This produces VRM-ready quaternions without coordinate-system conversion.
    """
    quats = np.zeros((len(_BONE_PAIRS), 4), dtype=np.float32)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    for i, (parent_idx, child_idx, _) in enumerate(_BONE_PAIRS):
        if parent_idx == child_idx:
            quats[i] = [0.0, 0.0, 0.0, 1.0]  # identity
            continue

        direction = landmarks[child_idx] - landmarks[parent_idx]
        length = float(np.linalg.norm(direction))
        if length < 1e-6:
            quats[i] = [0.0, 0.0, 0.0, 1.0]
            continue

        direction /= length
        quats[i] = _vec_to_quat(up, direction)

    return quats.astype(np.float16)


def _vec_to_quat(from_vec: np.ndarray, to_vec: np.ndarray) -> np.ndarray:
    """Shortest-arc quaternion rotating from_vec onto to_vec (xyzw)."""
    cross = np.cross(from_vec, to_vec)
    dot = float(np.dot(from_vec, to_vec))
    w = 1.0 + dot
    if w < 1e-6:
        # Vectors are anti-parallel — 180° rotation around any perpendicular axis
        perp = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if abs(from_vec[0]) > 0.9:
            perp = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        cross = np.cross(from_vec, perp)
        w = 0.0
    q = np.array([cross[0], cross[1], cross[2], w], dtype=np.float32)
    norm = float(np.linalg.norm(q))
    if norm < 1e-6:
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    return q / norm


def _reduce_face(face: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """Reduce 468-landmark face to 6 key landmarks as float16, or None."""
    if face is None or len(face) < max(_FACE_KEY_INDICES) + 1:
        return None
    return face[_FACE_KEY_INDICES].astype(np.float16)


def _to_float16_or_none(arr: Optional[np.ndarray]) -> Optional[np.ndarray]:
    if arr is None or arr.size == 0:
        return None
    return arr.astype(np.float16)
