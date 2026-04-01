"""PoseSmoother: Two-layer landmark smoothing + Catmull-Rom Bezier keyframe interpolation.

Layer 1 — Spatial: per-frame Gaussian blur over landmark coords (σ=1.5).
Layer 2 — Temporal: Exponential Moving Average across frames (α=0.7).
Interpolation — Cubic Bezier between keyframes using Catmull-Rom tangents.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# EMA weight — higher follows motion more closely, lower = smoother but laggy
_EMA_ALPHA = 0.7
# Gaussian σ for spatial smoothing (small kernel, applied per-joint)
_GAUSSIAN_SIGMA = 1.5
# Minimum displacement between frames to qualify as a new keyframe
# (in normalized coords — 0.02 = 2% of frame width)
_KEYFRAME_THRESHOLD = 0.02


class PoseSmoother:
    """Applies spatial + temporal smoothing to landmark arrays and detects keyframes.

    Usage:
        smoother = PoseSmoother()
        smoothed, is_keyframe = smoother.smooth(landmarks)
        if is_keyframe:
            store_keyframe(smoothed)
    """

    def __init__(
        self,
        ema_alpha: float = _EMA_ALPHA,
        gaussian_sigma: float = _GAUSSIAN_SIGMA,
        keyframe_threshold: float = _KEYFRAME_THRESHOLD,
    ) -> None:
        self._alpha = ema_alpha
        self._sigma = gaussian_sigma
        self._keyframe_threshold = keyframe_threshold
        self._ema_state: Optional[np.ndarray] = None
        self._last_keyframe: Optional[np.ndarray] = None

    def smooth(
        self, landmarks: np.ndarray
    ) -> Tuple[np.ndarray, bool]:
        """Smooth a (33, 3) landmark array and decide if it is a keyframe.

        Returns:
            (smoothed_landmarks, is_keyframe)
            is_keyframe=True when the frame differs enough from the last stored
            keyframe to be worth storing; False = interpolatable intermediate.
        """
        spatially = self._spatial_smooth(landmarks)
        temporally = self._temporal_smooth(spatially)
        is_keyframe = self._is_keyframe(temporally)
        if is_keyframe:
            self._last_keyframe = temporally.copy()
        return temporally, is_keyframe

    def reset(self) -> None:
        """Reset smoother state between clips."""
        self._ema_state = None
        self._last_keyframe = None

    # ------------------------------------------------------------------

    def _spatial_smooth(self, landmarks: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur across the landmark array (spatial axis).

        Treats the 33 joints as a 1-D signal and applies a 1-D Gaussian
        kernel of σ=_sigma. Each coordinate axis (x, y, z) is filtered
        independently. This removes high-frequency jitter within a single
        frame without blurring across time.
        """
        kernel = self._gaussian_kernel_1d(self._sigma)
        smoothed = np.empty_like(landmarks)
        for axis in range(3):
            smoothed[:, axis] = np.convolve(
                landmarks[:, axis], kernel, mode="same"
            )
        return smoothed

    def _temporal_smooth(self, landmarks: np.ndarray) -> np.ndarray:
        """Apply Exponential Moving Average across frames."""
        if self._ema_state is None:
            self._ema_state = landmarks.copy()
            return landmarks.copy()
        self._ema_state = (
            self._alpha * landmarks + (1.0 - self._alpha) * self._ema_state
        )
        return self._ema_state.copy()

    def _is_keyframe(self, landmarks: np.ndarray) -> bool:
        """Return True if landmarks differ enough from last keyframe."""
        if self._last_keyframe is None:
            return True
        mean_displacement = float(
            np.mean(np.linalg.norm(landmarks - self._last_keyframe, axis=1))
        )
        return mean_displacement >= self._keyframe_threshold

    @staticmethod
    def _gaussian_kernel_1d(sigma: float, truncate: float = 3.0) -> np.ndarray:
        """Build a normalized 1-D Gaussian kernel."""
        radius = int(truncate * sigma + 0.5)
        x = np.arange(-radius, radius + 1, dtype=np.float64)
        kernel = np.exp(-0.5 * (x / sigma) ** 2)
        return (kernel / kernel.sum()).astype(np.float32)


# ------------------------------------------------------------------
# Bezier / Catmull-Rom interpolation utilities
# ------------------------------------------------------------------

def interpolate_keyframes(
    keyframes: List[np.ndarray],
    timestamps: List[float],
    target_fps: float,
) -> List[np.ndarray]:
    """Interpolate between keyframes using Catmull-Rom splines.

    Produces a dense sequence of frames at `target_fps` by evaluating the
    Catmull-Rom cubic spline between each pair of consecutive keyframes.
    Catmull-Rom tangents are computed automatically from surrounding keyframes,
    giving natural ease-in/ease-out without manual tuning.

    Args:
        keyframes: List of (33, 3) landmark arrays at known timestamps.
        timestamps: Corresponding timestamps in seconds (same length as keyframes).
        target_fps: Output frame rate.

    Returns:
        List of (33, 3) arrays at uniform target_fps intervals.
    """
    if len(keyframes) < 2:
        return list(keyframes)

    total_duration = timestamps[-1] - timestamps[0]
    n_frames = max(2, int(round(total_duration * target_fps)))
    output_times = np.linspace(timestamps[0], timestamps[-1], n_frames)

    result: List[np.ndarray] = []
    for t in output_times:
        frame = _catmull_rom_at(keyframes, timestamps, t)
        result.append(frame)
    return result


def compute_bezier_tangents(
    keyframes: List[np.ndarray],
) -> List[np.ndarray]:
    """Pre-compute Catmull-Rom tangents for a list of keyframes.

    For keyframe i, tangent = 0.5 * (keyframe[i+1] - keyframe[i-1]).
    Endpoints use one-sided differences.

    Returns:
        List of tangent arrays, same length as keyframes. Each tangent has
        shape (33, 3).
    """
    n = len(keyframes)
    tangents: List[np.ndarray] = []
    for i in range(n):
        prev = keyframes[max(0, i - 1)]
        nxt = keyframes[min(n - 1, i + 1)]
        tangents.append(0.5 * (nxt - prev))
    return tangents


def _catmull_rom_at(
    keyframes: List[np.ndarray],
    timestamps: List[float],
    t: float,
) -> np.ndarray:
    """Evaluate Catmull-Rom spline at time t."""
    n = len(keyframes)
    # Find which segment t falls in
    seg = 0
    for i in range(n - 1):
        if timestamps[i] <= t <= timestamps[i + 1]:
            seg = i
            break
    else:
        if t >= timestamps[-1]:
            return keyframes[-1].copy()
        return keyframes[0].copy()

    t0, t1 = timestamps[seg], timestamps[seg + 1]
    span = t1 - t0
    if span < 1e-9:
        return keyframes[seg].copy()

    u = (t - t0) / span  # normalised [0, 1]

    p0 = keyframes[seg]
    p1 = keyframes[seg + 1]
    m0 = 0.5 * (keyframes[min(seg + 1, n - 1)] - keyframes[max(seg - 1, 0)])
    m1 = 0.5 * (keyframes[min(seg + 2, n - 1)] - keyframes[max(seg, 0)])

    # Cubic Hermite basis
    h00 = 2 * u**3 - 3 * u**2 + 1
    h10 = u**3 - 2 * u**2 + u
    h01 = -2 * u**3 + 3 * u**2
    h11 = u**3 - u**2

    return (h00 * p0 + h10 * span * m0 + h01 * p1 + h11 * span * m1).astype(
        np.float32
    )
