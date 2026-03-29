"""PoseRotation: Calculate bone rotations from MediaPipe landmarks using rest pose delta.

Each bone's rotation is computed by comparing its current orientation (direction vector)
to the rest pose orientation, then computing the quaternion that rotates the rest
vector onto the current vector. This gives hierarchical bone rotations suitable
for VRM humanoid animation.

Rest pose: T-pose with arms extended horizontally, legs straight down.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# MediaPipe body landmark indices (33 total)
# Each bone: (parent_idx, child_idx, vrm_bone_name)
BONE_HIERARCHY: List[Tuple[int, int, str]] = [
    (23, 24, "Hips"),           # Left hip → Right hip (hips center direction)
    (0, 9, "Spine"),            # Nose → Upper spine approximation
    (9, 12, "Chest"),           # Upper → Lower spine
    (12, 0, "UpperChest"),      # Lower spine → neck approximation
    (12, 11, "LeftShoulder"),   # Spine → Left shoulder
    (11, 13, "LeftUpperArm"),   # Left shoulder → elbow
    (13, 15, "LeftLowerArm"),   # Left elbow → wrist
    (12, 14, "RightShoulder"),  # Spine → Right shoulder
    (14, 16, "RightUpperArm"),  # Right shoulder → elbow
    (16, 18, "RightLowerArm"),  # Right elbow → wrist
    (23, 25, "LeftUpperLeg"),   # Left hip → knee
    (25, 27, "LeftLowerLeg"),   # Left knee → ankle
    (24, 26, "RightUpperLeg"),  # Right hip → knee
    (26, 28, "RightLowerLeg"),  # Right knee → ankle
    (0, 7, "Head"),             # Nose → left eye (head direction approximation)
]

# MediaPipe landmark names for reference
LANDMARK_NAMES = {
    0: "nose", 1: "left_eye_inner", 2: "left_eye", 3: "left_eye_outer",
    4: "right_eye_inner", 5: "right_eye", 6: "right_eye_outer",
    7: "left_ear", 8: "right_ear", 9: "mouth_left", 10: "mouth_right",
    11: "left_shoulder", 12: "right_shoulder", 13: "left_elbow",
    14: "right_elbow", 15: "left_wrist", 16: "right_wrist",
    17: "left_pinky", 18: "right_pinky", 19: "left_index", 20: "right_index",
    21: "left_thumb", 22: "right_thumb", 23: "left_hip", 24: "right_hip",
    25: "left_knee", 26: "right_knee", 27: "left_ankle", 28: "right_ankle",
    29: "left_heel", 30: "right_heel", 31: "left_foot_index", 32: "right_foot_index",
}


def _quat_from_two_vectors(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """Compute quaternion [x, y, z, w] that rotates v1 onto v2 (shortest arc)."""
    v1 = v1 / (np.linalg.norm(v1) + 1e-8)
    v2 = v2 / (np.linalg.norm(v2) + 1e-8)

    dot = np.dot(v1, v2)
    if dot > 0.99999:
        return np.array([0, 0, 0, 1], dtype=np.float32)
    if dot < -0.99999:
        # 180° rotation — find perpendicular axis
        perp = np.array([1, 0, 0], dtype=np.float32)
        if abs(v1[0]) > 0.9:
            perp = np.array([0, 1, 0], dtype=np.float32)
        axis = np.cross(v1, perp)
        axis = axis / (np.linalg.norm(axis) + 1e-8)
        return np.array([axis[0], axis[1], axis[2], 0], dtype=np.float32)

    cross = np.cross(v1, v2)
    w = 1.0 + dot
    q = np.array([cross[0], cross[1], cross[2], w], dtype=np.float32)
    q = q / (np.linalg.norm(q) + 1e-8)
    return q


def _quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiply two quaternions [x, y, z, w]."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    ], dtype=np.float32)


def _quat_inverse(q: np.ndarray) -> np.ndarray:
    """Return inverse of quaternion [x, y, z, w]."""
    return np.array([-q[0], -q[1], -q[2], q[3]], dtype=np.float32)


class PoseRotationCalculator:
    """Calculates bone rotations from MediaPipe landmarks using rest pose delta.

    Usage:
        calc = PoseRotationCalculator()
        # Set rest pose from T-pose frame
        calc.set_rest_pose(t_pose_landmarks)  # shape (33, 3)
        # For each frame:
        rotations = calc.calculate(frame_landmarks)  # shape (N_bones, 4)
    """

    def __init__(self) -> None:
        self._rest_bone_vectors: Dict[str, np.ndarray] = {}
        self._rest_set = False

    @property
    def bone_names(self) -> List[str]:
        return [bone[2] for bone in BONE_HIERARCHY]

    @property
    def num_bones(self) -> int:
        return len(BONE_HIERARCHY)

    def set_rest_pose(self, landmarks: np.ndarray) -> None:
        """Set the rest pose (T-pose) from which deltas are computed.

        Args:
            landmarks: shape (33, 3) — MediaPipe body landmarks in T-pose.
        """
        self._rest_bone_vectors.clear()
        for parent_idx, child_idx, bone_name in BONE_HIERARCHY:
            if parent_idx < len(landmarks) and child_idx < len(landmarks):
                vec = landmarks[child_idx] - landmarks[parent_idx]
                norm = np.linalg.norm(vec)
                if norm > 1e-6:
                    self._rest_bone_vectors[bone_name] = vec / norm
                else:
                    self._rest_bone_vectors[bone_name] = np.array([0, -1, 0], dtype=np.float32)
            else:
                self._rest_bone_vectors[bone_name] = np.array([0, -1, 0], dtype=np.float32)
        self._rest_set = True
        logger.info(f"Rest pose set with {len(self._rest_bone_vectors)} bones")

    def set_auto_rest_pose(self) -> None:
        """Set rest pose to a standard T-pose (arms horizontal, legs vertical)."""
        tpose = np.zeros((33, 3), dtype=np.float32)

        # Head/nose at top center
        tpose[0] = [0.5, 0.2, 0.0]    # nose
        tpose[7] = [0.35, 0.25, 0.0]   # left ear
        tpose[8] = [0.65, 0.25, 0.0]   # right ear
        tpose[9] = [0.45, 0.35, 0.0]   # mouth left
        tpose[10] = [0.55, 0.35, 0.0]  # mouth right

        # Shoulders (horizontal, T-pose)
        tpose[11] = [0.35, 0.4, 0.0]   # left shoulder
        tpose[12] = [0.65, 0.4, 0.0]   # right shoulder

        # Elbows (arms extended)
        tpose[13] = [0.15, 0.4, 0.0]   # left elbow
        tpose[14] = [0.85, 0.4, 0.0]   # right elbow

        # Wrists (arms fully extended)
        tpose[15] = [0.0, 0.4, 0.0]    # left wrist
        tpose[16] = [1.0, 0.4, 0.0]    # right wrist

        # Fingers (at wrists for T-pose)
        for i in [17, 19, 21]:
            tpose[i] = tpose[15]
        for i in [18, 20, 22]:
            tpose[i] = tpose[16]

        # Hips
        tpose[23] = [0.45, 0.6, 0.0]   # left hip
        tpose[24] = [0.55, 0.6, 0.0]   # right hip

        # Knees (straight down)
        tpose[25] = [0.45, 0.8, 0.0]   # left knee
        tpose[26] = [0.55, 0.8, 0.0]   # right knee

        # Ankles (straight down)
        tpose[27] = [0.45, 1.0, 0.0]   # left ankle
        tpose[28] = [0.55, 1.0, 0.0]   # right ankle

        # Heels and feet
        tpose[29] = [0.45, 1.0, 0.05]  # left heel
        tpose[30] = [0.55, 1.0, 0.05]  # right heel
        tpose[31] = [0.45, 1.0, -0.1]  # left foot index
        tpose[32] = [0.55, 1.0, -0.1]  # right foot index

        self.set_rest_pose(tpose)

    def calculate(self, landmarks: np.ndarray) -> np.ndarray:
        """Calculate bone rotations for a frame.

        Args:
            landmarks: shape (33, 3) — MediaPipe body landmarks for this frame.

        Returns:
            shape (num_bones, 4) — quaternions [x, y, z, w] for each bone.
        """
        if not self._rest_set:
            self.set_auto_rest_pose()

        rotations = np.zeros((self.num_bones, 4), dtype=np.float32)
        rotations[:, 3] = 1.0  # identity quaternion default

        parent_rotations: Dict[str, np.ndarray] = {"root": np.array([0, 0, 0, 1], dtype=np.float32)}

        for i, (parent_idx, child_idx, bone_name) in enumerate(BONE_HIERARCHY):
            if parent_idx >= len(landmarks) or child_idx >= len(landmarks):
                continue

            current_vec = landmarks[child_idx] - landmarks[parent_idx]
            current_norm = np.linalg.norm(current_vec)
            if current_norm < 1e-6:
                continue
            current_vec = current_vec / current_norm

            rest_vec = self._rest_bone_vectors.get(bone_name)
            if rest_vec is None:
                rest_vec = np.array([0, -1, 0], dtype=np.float32)

            local_rotation = _quat_from_two_vectors(rest_vec, current_vec)

            parent_name = self._get_parent_bone(bone_name)
            parent_rot = parent_rotations.get(parent_name, np.array([0, 0, 0, 1], dtype=np.float32))

            world_rotation = _quat_multiply(parent_rot, local_rotation)
            rotations[i] = world_rotation
            parent_rotations[bone_name] = world_rotation

        return rotations

    def calculate_with_confidence(
        self, landmarks: np.ndarray, visibilities: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate rotations with per-bone confidence scores.

        Returns:
            (rotations, confidences) where:
                rotations: shape (num_bones, 4) — quaternions
                confidences: shape (num_bones,) — 0.0 to 1.0 per bone
        """
        rotations = self.calculate(landmarks)

        confidences = np.ones(self.num_bones, dtype=np.float32)
        if visibilities is not None:
            for i, (parent_idx, child_idx, _) in enumerate(BONE_HIERARCHY):
                parent_conf = visibilities[parent_idx] if parent_idx < len(visibilities) else 1.0
                child_conf = visibilities[child_idx] if child_idx < len(visibilities) else 1.0
                confidences[i] = min(parent_conf, child_conf)

        return rotations, confidences

    def _get_parent_bone(self, bone_name: str) -> str:
        """Get the parent bone name for hierarchical rotation computation."""
        hierarchy = {
            "Hips": "root",
            "Spine": "Hips",
            "Chest": "Spine",
            "UpperChest": "Chest",
            "LeftShoulder": "UpperChest",
            "LeftUpperArm": "LeftShoulder",
            "LeftLowerArm": "LeftUpperArm",
            "RightShoulder": "UpperChest",
            "RightUpperArm": "RightShoulder",
            "RightLowerArm": "RightUpperArm",
            "LeftUpperLeg": "Hips",
            "LeftLowerLeg": "LeftUpperLeg",
            "RightUpperLeg": "Hips",
            "RightLowerLeg": "RightUpperLeg",
            "Head": "UpperChest",
        }
        return hierarchy.get(bone_name, "root")
