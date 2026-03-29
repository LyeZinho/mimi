"""PoseValidator: Multi-stage validation pipeline for MediaPipe pose landmarks.

Stages:
  1. Confidence check — visibility threshold per landmark
  2. Anatomical validation — proportional joint distances, detect impossibilities
  3. Temporal coherence — velocity limit per joint, per-joint discard (not whole frame)
  4. Outlier rejection — rolling mean + 2σ deviation detection
"""

import logging
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# MediaPipe body landmark indices (33 total)
# Key joints used for anatomical validation
_JOINT = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

# Pairs of adjacent joints that should have similar lengths (limb symmetry)
_LIMB_PAIRS: List[Tuple[Tuple[int, int], Tuple[int, int]]] = [
    # (upper_limb, lower_limb) — each is (joint_a_idx, joint_b_idx)
    ((_JOINT["left_shoulder"], _JOINT["left_elbow"]),
     (_JOINT["left_elbow"], _JOINT["left_wrist"])),
    ((_JOINT["right_shoulder"], _JOINT["right_elbow"]),
     (_JOINT["right_elbow"], _JOINT["right_wrist"])),
    ((_JOINT["left_hip"], _JOINT["left_knee"]),
     (_JOINT["left_knee"], _JOINT["left_ankle"])),
    ((_JOINT["right_hip"], _JOINT["right_knee"]),
     (_JOINT["right_knee"], _JOINT["right_ankle"])),
]

# Confidence threshold per landmark
_CONFIDENCE_THRESHOLD = 0.5
# Minimum ratio of landmarks that must pass confidence check
_MIN_PASSING_RATIO = 0.6
# Max ratio between adjacent limb lengths before flagging anatomical issue
_ANATOMY_RATIO_MAX = 3.0
# Max displacement per joint between consecutive frames (in normalized coords)
_MAX_VELOCITY = 0.25
# Rolling window size for outlier detection
_OUTLIER_WINDOW = 10
# Number of standard deviations for outlier detection
_OUTLIER_SIGMA = 2.0


class ValidationResult:
    """Result of validating a single frame."""

    def __init__(
        self,
        valid: bool,
        landmarks: Optional[np.ndarray],
        invalid_joints: Optional[Set[int]] = None,
        reason: str = "",
    ) -> None:
        self.valid = valid
        # Shape (33, 3) or None if frame is fully discarded
        self.landmarks = landmarks
        # Joints that were individually discarded (to be interpolated)
        self.invalid_joints: Set[int] = invalid_joints or set()
        self.reason = reason

    def __repr__(self) -> str:
        return (
            f"ValidationResult(valid={self.valid}, "
            f"invalid_joints={self.invalid_joints}, reason={self.reason!r})"
        )


class PoseValidator:
    """Validates MediaPipe body landmark arrays through 4 sequential stages.

    Usage:
        validator = PoseValidator()
        result = validator.validate(landmarks_array, visibilities_array)
        if result.valid:
            use_landmarks(result.landmarks)
    """

    def __init__(
        self,
        confidence_threshold: float = _CONFIDENCE_THRESHOLD,
        min_passing_ratio: float = _MIN_PASSING_RATIO,
        anatomy_ratio_max: float = _ANATOMY_RATIO_MAX,
        max_velocity: float = _MAX_VELOCITY,
        outlier_window: int = _OUTLIER_WINDOW,
        outlier_sigma: float = _OUTLIER_SIGMA,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._min_passing_ratio = min_passing_ratio
        self._anatomy_ratio_max = anatomy_ratio_max
        self._max_velocity = max_velocity
        self._outlier_sigma = outlier_sigma

        # State for temporal coherence and outlier detection
        self._prev_landmarks: Optional[np.ndarray] = None
        # Rolling history per joint: deque of shape-(3,) arrays
        self._history: List[deque] = [
            deque(maxlen=outlier_window) for _ in range(33)
        ]

    def validate(
        self,
        landmarks: np.ndarray,
        visibilities: Optional[np.ndarray] = None,
    ) -> ValidationResult:
        """Run all 4 validation stages on a frame's landmarks.

        Args:
            landmarks: shape (33, 3) float32 — MediaPipe body landmarks (x, y, z).
            visibilities: shape (33,) float32 — per-landmark visibility/confidence.
                          If None, stage 1 is skipped.

        Returns:
            ValidationResult with valid=True if frame passes, landmarks possibly
            with outlier joints zeroed out, and invalid_joints set.
        """
        if landmarks is None or landmarks.shape != (33, 3):
            return ValidationResult(valid=False, landmarks=None, reason="invalid_shape")

        # Stage 1: Confidence check
        if visibilities is not None:
            result = self._check_confidence(landmarks, visibilities)
            if not result.valid:
                return result

        # Stage 2: Anatomical validation
        result = self._check_anatomy(landmarks)
        if not result.valid:
            return result

        # Stage 3: Temporal coherence (per-joint velocity)
        invalid_joints: Set[int] = set()
        if self._prev_landmarks is not None:
            invalid_joints = self._check_temporal(landmarks)

        # Stage 4: Outlier rejection
        outlier_joints = self._check_outliers(landmarks)
        invalid_joints |= outlier_joints

        # Build cleaned landmarks: invalid joints carry forward from prev frame
        cleaned = landmarks.copy()
        if invalid_joints and self._prev_landmarks is not None:
            for j in invalid_joints:
                cleaned[j] = self._prev_landmarks[j]

        self._prev_landmarks = cleaned.copy()
        for j in range(33):
            self._history[j].append(cleaned[j].copy())

        return ValidationResult(
            valid=True,
            landmarks=cleaned,
            invalid_joints=invalid_joints,
            reason="ok",
        )

    def reset(self) -> None:
        """Reset temporal state (call between separate video clips)."""
        self._prev_landmarks = None
        for h in self._history:
            h.clear()

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _check_confidence(
        self, landmarks: np.ndarray, visibilities: np.ndarray
    ) -> ValidationResult:
        """Stage 1: Reject frame if too many landmarks have low confidence."""
        passing = int(np.sum(visibilities >= self._confidence_threshold))
        ratio = passing / len(visibilities)
        if ratio < self._min_passing_ratio:
            logger.debug(
                f"Confidence check failed: {passing}/33 landmarks above threshold "
                f"({ratio:.1%} < {self._min_passing_ratio:.1%})"
            )
            return ValidationResult(
                valid=False,
                landmarks=None,
                reason=f"confidence_low:{ratio:.2f}",
            )
        return ValidationResult(valid=True, landmarks=landmarks)

    def _check_anatomy(self, landmarks: np.ndarray) -> ValidationResult:
        """Stage 2: Validate anatomical proportions between adjacent limb segments."""
        for (a1, b1), (a2, b2) in _LIMB_PAIRS:
            seg1 = float(np.linalg.norm(landmarks[a1] - landmarks[b1]))
            seg2 = float(np.linalg.norm(landmarks[a2] - landmarks[b2]))

            if seg1 < 1e-6 or seg2 < 1e-6:
                # Zero-length segment — likely occluded, skip this pair
                continue

            ratio = max(seg1, seg2) / min(seg1, seg2)
            if ratio > self._anatomy_ratio_max:
                logger.debug(
                    f"Anatomical check failed: segment ratio {ratio:.2f} "
                    f"(joints {a1}-{b1} vs {a2}-{b2})"
                )
                return ValidationResult(
                    valid=False,
                    landmarks=None,
                    reason=f"anatomy_ratio:{ratio:.2f}",
                )
        return ValidationResult(valid=True, landmarks=landmarks)

    def _check_temporal(self, landmarks: np.ndarray) -> Set[int]:
        """Stage 3: Detect per-joint velocity violations vs previous frame.

        Returns set of joint indices that exceeded max velocity.
        Does NOT discard the whole frame.
        """
        assert self._prev_landmarks is not None
        delta = np.linalg.norm(landmarks - self._prev_landmarks, axis=1)  # (33,)
        invalid: Set[int] = set()
        for j, d in enumerate(delta):
            if d > self._max_velocity:
                logger.debug(f"Temporal velocity exceeded for joint {j}: {d:.4f}")
                invalid.add(j)
        return invalid

    def _check_outliers(self, landmarks: np.ndarray) -> Set[int]:
        """Stage 4: Detect joints deviating >outlier_sigma from rolling mean.

        Returns set of outlier joint indices.
        """
        invalid: Set[int] = set()
        for j in range(33):
            history = self._history[j]
            if len(history) < 3:
                continue  # Not enough history yet
            history_arr = np.stack(list(history))  # (N, 3)
            mean = history_arr.mean(axis=0)
            std = history_arr.std(axis=0).mean()  # scalar std across xyz
            if std < 1e-6:
                continue
            deviation = float(np.linalg.norm(landmarks[j] - mean))
            if deviation > self._outlier_sigma * std:
                logger.debug(
                    f"Outlier detected for joint {j}: deviation={deviation:.4f}, "
                    f"sigma_threshold={self._outlier_sigma * std:.4f}"
                )
                invalid.add(j)
        return invalid
