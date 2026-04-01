"""SkeletonStorage: Efficient msgpack-based storage for skeleton pose frames with JSON indexing."""

import logging
import json
import msgpack
import numpy as np
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class SkeletonFrame:
    """Represents a single skeleton frame with pose landmarks."""
    
    frame_id: int
    timestamp: float
    body_pose: np.ndarray
    left_hand: np.ndarray
    right_hand: np.ndarray
    face: np.ndarray
    metadata: Optional[Dict[str, Any]] = None


class SkeletonStorage:
    """Efficiently stores skeleton pose frames in msgpack format with JSON index."""

    def __init__(
        self,
        base_path: Path,
        name: str,
        mode: str = "w",
        fps: float = 30.0
    ) -> None:
        """
        Initialize SkeletonStorage.

        Args:
            base_path: Directory path for storage files.
            name: Name prefix for generated files (e.g., 'sequence' creates sequence.msgpack).
            mode: 'w' for write (default), 'r' for read.
            fps: Frames per second for metadata (used in write mode).
        """
        self.base_path = Path(base_path)
        self.name = name
        self.mode = mode
        self.fps = fps
        
        if mode not in ("r", "w"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'r' or 'w'.")
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self._frames: Dict[int, SkeletonFrame] = {}
        self._index: Dict[str, Any] = {}
        
        if mode == "r":
            self._load()
        
        logger.info(f"SkeletonStorage initialized: name={name}, mode={mode}, fps={fps}")

    @property
    def total_frames(self) -> int:
        """Total number of frames in storage."""
        if self.mode == "w":
            return len(self._frames)
        return self._index.get("total_frames", 0)

    def add_frame(self, frame: SkeletonFrame) -> None:
        """
        Add a frame to storage (write mode only).

        Args:
            frame: SkeletonFrame to add.

        Raises:
            ValueError: If not in write mode.
        """
        if self.mode != "w":
            raise ValueError("Cannot add frames in read mode")
        
        self._frames[frame.frame_id] = frame
        logger.debug(f"Added frame {frame.frame_id} (timestamp={frame.timestamp})")

    def get_frame(self, frame_id: int) -> Optional[SkeletonFrame]:
        """
        Retrieve a frame by ID (read mode only).

        Args:
            frame_id: Frame ID to retrieve.

        Returns:
            SkeletonFrame if found, None otherwise.
        """
        if self.mode == "w":
            return None
        
        if frame_id not in self._frames:
            return None
        
        return self._frames[frame_id]

    def finalize(self) -> None:
        """
        Finalize storage by writing msgpack data, index, and metadata (write mode only).

        Writes three files:
        - {name}.msgpack: Binary msgpack data of all frames
        - {name}_index.json: JSON index with frame_ids and timestamps
        - {name}_metadata.json: JSON metadata with fps and duration
        """
        if self.mode != "w":
            logger.warning("finalize() called in read mode, skipping")
            return
        
        self._write_data()
        self._write_index()
        self._write_metadata()
        logger.info(f"Finalized storage: {self.total_frames} frames written")

    def _write_data(self) -> None:
        """Write all frames to msgpack file."""
        msgpack_file = self.base_path / f"{self.name}.msgpack"
        
        frames_list = []
        for frame_id in sorted(self._frames.keys()):
            frame = self._frames[frame_id]
            frame_data = {
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "body_pose": frame.body_pose.tolist(),
                "left_hand": frame.left_hand.tolist(),
                "right_hand": frame.right_hand.tolist(),
                "face": frame.face.tolist(),
                "metadata": frame.metadata
            }
            frames_list.append(frame_data)
        
        with open(msgpack_file, "wb") as f:
            f.write(msgpack.packb(frames_list, use_bin_type=True))
        
        logger.debug(f"Wrote {len(frames_list)} frames to {msgpack_file}")

    def _write_index(self) -> None:
        """Write index file with frame IDs and timestamps."""
        index_file = self.base_path / f"{self.name}_index.json"
        
        index_data = {
            "total_frames": self.total_frames,
            "fps": self.fps,
            "frame_ids": sorted(self._frames.keys()),
            "timestamps": [self._frames[fid].timestamp for fid in sorted(self._frames.keys())]
        }
        
        with open(index_file, "w") as f:
            json.dump(index_data, f, indent=2)
        
        logger.debug(f"Wrote index to {index_file}")

    def _write_metadata(self) -> None:
        """Write metadata file with fps and duration."""
        metadata_file = self.base_path / f"{self.name}_metadata.json"
        
        if self.total_frames > 0:
            duration_sec = (self.total_frames - 1) / self.fps
        else:
            duration_sec = 0.0
        
        metadata = {
            "name": self.name,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration_sec": duration_sec
        }
        
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.debug(f"Wrote metadata to {metadata_file}")

    def _load(self) -> None:
        """Load storage from files (read mode only)."""
        msgpack_file = self.base_path / f"{self.name}.msgpack"
        index_file = self.base_path / f"{self.name}_index.json"
        metadata_file = self.base_path / f"{self.name}_metadata.json"
        
        if not msgpack_file.exists():
            logger.warning(f"msgpack file not found: {msgpack_file}")
            return
        
        if index_file.exists():
            with open(index_file, "r") as f:
                self._index = json.load(f)
        
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                self.fps = metadata.get("fps", self.fps)
        
        with open(msgpack_file, "rb") as f:
            frames_list = msgpack.unpackb(f.read(), raw=False)
        
        for frame_data in frames_list:
            frame = SkeletonFrame(
                frame_id=frame_data["frame_id"],
                timestamp=frame_data["timestamp"],
                body_pose=np.array(frame_data["body_pose"], dtype=np.float32),
                left_hand=np.array(frame_data["left_hand"], dtype=np.float32),
                right_hand=np.array(frame_data["right_hand"], dtype=np.float32),
                face=np.array(frame_data["face"], dtype=np.float32),
                metadata=frame_data.get("metadata")
            )
            self._frames[frame.frame_id] = frame
        
        logger.info(f"Loaded {len(self._frames)} frames from storage")

    def close(self) -> None:
        """Close storage and release resources."""
        logger.debug("SkeletonStorage closed")
