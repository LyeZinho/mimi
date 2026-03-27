# ML-Driven Pose Capture & Animation Database System

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers/executing-plans to implement this plan task-by-task in subagent-driven development.

**Goal:** Build a machine learning-driven pose capture system that analyzes videos (OpenCV + FFmpeg), extracts skeleton transformations, stores them efficiently, and enables the Orchestrator to playback complex animated poses on VRM 3D models.

**Architecture:** 
Three-layer system: (1) **Video Analysis Layer** (OpenCV + MediaPipe) captures human poses from video files → (2) **Skeleton Database Layer** (msgpack/Parquet) stores keyframe-indexed pose data → (3) **Playback Layer** (WebSocket → Three.js) retrieves and executes stored poses on VRM.

The system maintains **full backward compatibility** with existing expression-based control while adding sophisticated skeletal animation playback.

**Tech Stack:** 
- Backend: MediaPipe (pose detection), FFmpeg (video parsing), msgpack/Parquet (efficient storage)
- Frontend: Three.js, Pixiv three-vrm (VRM execution)
- Protocol: WebSocket (Orchestrator → Frontend), JSON (pose metadata)
- Pattern: Mixamo → VRM bone mapping (existing, reused)

---

## Phase 1: Pose Detection & Analysis (Backend)

### Task 1: Pose Detector Module (MediaPipe Integration)

**Files:**
- Create: `agent/ml/pose_detector.py`
- Create: `agent/ml/__init__.py`
- Test: `tests/unit/test_pose_detector.py`

**Overview:** Wraps MediaPipe Holistic pose detection. Extracts 3D landmarks (body, hands, face) from video frames. Returns normalized pose format.

**Step 1: Write failing test**

```python
# tests/unit/test_pose_detector.py
import pytest
import numpy as np
from agent.ml.pose_detector import PoseDetector

class TestPoseDetector:
    def test_detector_init(self):
        detector = PoseDetector()
        assert detector is not None
        assert hasattr(detector, 'process_frame')
    
    def test_process_frame_returns_landmarks(self):
        detector = PoseDetector()
        # Create dummy frame (BGR, 480x640x3)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.process_frame(frame)
        
        assert result is not None
        assert 'body_landmarks' in result
        assert 'hand_landmarks' in result
        assert 'face_landmarks' in result
        assert isinstance(result['body_landmarks'], list)
    
    def test_normalize_landmarks(self):
        detector = PoseDetector()
        # Create synthetic landmarks
        landmarks = {
            'body_landmarks': [[0.5, 0.5, 0.9], [0.6, 0.6, 0.95]],  # [x, y, z]
        }
        normalized = detector.normalize_landmarks(landmarks)
        
        assert 'body' in normalized
        assert len(normalized['body']) == 2
        # Check normalization: should be in [0, 1]
        for lm in normalized['body']:
            assert 0 <= lm[0] <= 1
            assert 0 <= lm[1] <= 1
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_pose_detector.py -v
# Expected: FAILED - ModuleNotFoundError: No module named 'agent.ml'
```

**Step 3: Implement PoseDetector**

```python
# agent/ml/pose_detector.py
"""
Pose Detector - MediaPipe-based human pose extraction from video frames
"""
import mediapipe as mp
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PoseDetector:
    """Detects human pose (body, hands, face) from video frames using MediaPipe."""
    
    def __init__(self, static_image_mode: bool = False):
        self.mp_holistic = mp.solutions.holistic
        self.holistic = self.mp_holistic.Holistic(
            static_image_mode=static_image_mode,
            model_complexity=1,  # 0=light, 1=full
            smooth_landmarks=True,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        self.frame_count = 0
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Process a single video frame and extract landmarks.
        
        Args:
            frame: BGR image (H x W x 3) from OpenCV
            
        Returns:
            Dict with keys:
            - body_landmarks: List[List[x, y, z, visibility]]
            - hand_landmarks_left: List[List[x, y, z]]
            - hand_landmarks_right: List[List[x, y, z]]
            - face_landmarks: List[List[x, y, z]]
            - success: bool (True if detected)
        """
        self.frame_count += 1
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(frame_rgb)
        
        output = {
            'body_landmarks': [],
            'hand_landmarks_left': [],
            'hand_landmarks_right': [],
            'face_landmarks': [],
            'success': False,
            'frame_id': self.frame_count
        }
        
        if results.pose_landmarks:
            output['body_landmarks'] = self._landmarks_to_list(results.pose_landmarks)
            output['success'] = True
        
        if results.left_hand_landmarks:
            output['hand_landmarks_left'] = self._landmarks_to_list(results.left_hand_landmarks)
        
        if results.right_hand_landmarks:
            output['hand_landmarks_right'] = self._landmarks_to_list(results.right_hand_landmarks)
        
        if results.face_landmarks:
            output['face_landmarks'] = self._landmarks_to_list(results.face_landmarks)
        
        return output
    
    @staticmethod
    def _landmarks_to_list(landmarks) -> List[List[float]]:
        """Convert MediaPipe landmarks to list of [x, y, z, visibility]."""
        return [[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks.landmark]
    
    def normalize_landmarks(self, landmarks: Dict[str, List]) -> Dict[str, np.ndarray]:
        """
        Normalize landmarks to [0, 1] range.
        
        Args:
            landmarks: Output from process_frame
            
        Returns:
            Dict with numpy arrays, normalized to [0, 1]
        """
        output = {}
        
        for key, lms in landmarks.items():
            if not lms or key in ['success', 'frame_id']:
                continue
            
            lms_array = np.array(lms)
            # Take only [x, y, z] columns
            if lms_array.shape[1] >= 3:
                lms_array = lms_array[:, :3]
            
            # Already in [0, 1] from MediaPipe, but ensure it
            lms_array = np.clip(lms_array, 0, 1)
            output[key.replace('_landmarks', '')] = lms_array
        
        return output
    
    def close(self):
        """Release MediaPipe resources."""
        self.holistic.close()
    
    def __del__(self):
        self.close()

# agent/ml/__init__.py
from agent.ml.pose_detector import PoseDetector

__all__ = ['PoseDetector']
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_pose_detector.py -v
# Expected: PASSED (3 tests)
```

**Step 5: Commit**

```bash
git add agent/ml/pose_detector.py agent/ml/__init__.py tests/unit/test_pose_detector.py
git commit -m "feat(ml): add pose detector using MediaPipe Holistic"
```

---

### Task 2: Video Frame Extractor (FFmpeg Integration)

**Files:**
- Create: `agent/ml/video_extractor.py`
- Test: `tests/unit/test_video_extractor.py`

**Overview:** Extracts frames from video files using FFmpeg. Handles various video codecs. Returns frame iterator with metadata (timestamp, fps).

**Step 1: Write failing test**

```python
# tests/unit/test_video_extractor.py
import pytest
import numpy as np
import tempfile
import os
from agent.ml.video_extractor import VideoExtractor

class TestVideoExtractor:
    @pytest.fixture
    def dummy_video_path(self):
        """Create a dummy video file for testing."""
        # Create a simple test video using FFmpeg
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            video_path = f.name
        
        # Generate video with ffmpeg-python or subprocess
        os.system(f"ffmpeg -f lavfi -i testsrc=s=320x240:d=1 -f lavfi -i sine=f=1000:d=1 {video_path} -y -loglevel quiet")
        
        yield video_path
        
        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
    
    def test_extractor_init(self, dummy_video_path):
        extractor = VideoExtractor(dummy_video_path)
        assert extractor is not None
        assert extractor.fps > 0
        assert extractor.total_frames > 0
        assert extractor.width > 0
        assert extractor.height > 0
    
    def test_iterate_frames(self, dummy_video_path):
        extractor = VideoExtractor(dummy_video_path)
        frames = []
        
        for frame, timestamp in extractor.iterate_frames():
            frames.append(frame)
            assert frame.shape[2] == 3  # BGR
            assert isinstance(timestamp, float)
        
        assert len(frames) > 0
        extractor.close()
```

**Step 2: Run test (will fail)**

```bash
pytest tests/unit/test_video_extractor.py -v
# Expected: FAILED - ModuleNotFoundError
```

**Step 3: Implement VideoExtractor**

```python
# agent/ml/video_extractor.py
"""
Video Frame Extractor - FFmpeg-based video frame extraction
"""
import subprocess
import numpy as np
from typing import Iterator, Tuple
import logging

logger = logging.getLogger(__name__)

class VideoExtractor:
    """Extracts frames from video files using FFmpeg."""
    
    def __init__(self, video_path: str, fps_override: int = None):
        """
        Initialize video extractor.
        
        Args:
            video_path: Path to video file
            fps_override: Override detected FPS (for testing)
        """
        self.video_path = video_path
        self.fps = fps_override or self._detect_fps()
        self.total_frames = self._detect_frame_count()
        self.width, self.height = self._detect_resolution()
        self._process = None
    
    def _detect_fps(self) -> float:
        """Detect video FPS using ffprobe."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1:noescapes=1',
            self.video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        fps_str = result.stdout.strip()
        
        # Parse "30/1" or "30"
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            return num / den
        return float(fps_str) if fps_str else 30.0
    
    def _detect_frame_count(self) -> int:
        """Detect total frame count."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-count_packets',
            '-show_entries', 'stream=nb_read_packets',
            '-of', 'csv=p=0',
            self.video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        count_str = result.stdout.strip()
        return int(count_str) if count_str else 0
    
    def _detect_resolution(self) -> Tuple[int, int]:
        """Detect video resolution."""
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            self.video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        dims = result.stdout.strip().split(',')
        return int(dims[0]), int(dims[1])
    
    def iterate_frames(self) -> Iterator[Tuple[np.ndarray, float]]:
        """
        Iterate frames from video.
        
        Yields:
            (frame, timestamp) where frame is BGR numpy array, timestamp in seconds
        """
        cmd = [
            'ffmpeg',
            '-i', self.video_path,
            '-f', 'image2pipe',
            '-pix_fmt', 'bgr24',
            '-vf', f'scale={self.width}:{self.height}',
            '-c:v', 'rawvideo',
            '-'
        ]
        
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10 ** 8
        )
        
        frame_id = 0
        bytes_per_frame = self.width * self.height * 3
        
        while True:
            frame_data = self._process.stdout.read(bytes_per_frame)
            if not frame_data:
                break
            
            frame = np.frombuffer(frame_data, dtype=np.uint8)
            frame = frame.reshape((self.height, self.width, 3))
            
            timestamp = frame_id / self.fps
            frame_id += 1
            
            yield frame, timestamp
        
        self._process.wait()
    
    def close(self):
        """Cleanup resources."""
        if self._process:
            self._process.terminate()

```

**Step 4: Run test to verify**

```bash
pytest tests/unit/test_video_extractor.py -v
# Expected: PASSED (2 tests)
```

**Step 5: Commit**

```bash
git add agent/ml/video_extractor.py tests/unit/test_video_extractor.py
git commit -m "feat(ml): add video frame extractor using FFmpeg"
```

---

## Phase 2: Skeleton Data Storage & Indexing

### Task 3: Skeleton Pose Storage (msgpack Format)

**Files:**
- Create: `agent/ml/skeleton_storage.py`
- Create: `data/pose_database/` (directory)
- Test: `tests/unit/test_skeleton_storage.py`

**Overview:** Stores pose keyframes in efficient msgpack format. Index for fast lookup. Schema: keyframe ID → pose data.

**Step 1: Write failing test**

```python
# tests/unit/test_skeleton_storage.py
import pytest
import numpy as np
import tempfile
import os
from agent.ml.skeleton_storage import SkeletonStorage, SkeletonFrame

class TestSkeletonStorage:
    @pytest.fixture
    def temp_storage_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_skeleton_frame_creation(self):
        frame = SkeletonFrame(
            frame_id=0,
            timestamp=0.0,
            body_pose=np.random.rand(33, 3),
            left_hand=np.random.rand(21, 3),
            right_hand=np.random.rand(21, 3),
            face=np.random.rand(468, 3)
        )
        
        assert frame.frame_id == 0
        assert frame.timestamp == 0.0
        assert frame.body_pose.shape == (33, 3)
    
    def test_storage_write_and_read(self, temp_storage_path):
        storage = SkeletonStorage(temp_storage_path, name="test_pose")
        
        # Write frames
        for i in range(5):
            frame = SkeletonFrame(
                frame_id=i,
                timestamp=i * 0.033,
                body_pose=np.ones((33, 3)) * i,
                left_hand=None,
                right_hand=None,
                face=None
            )
            storage.add_frame(frame)
        
        storage.finalize()  # Write index
        
        # Read frames
        read_storage = SkeletonStorage(temp_storage_path, name="test_pose", mode='r')
        
        assert read_storage.total_frames == 5
        assert read_storage.fps == 30.0  # Default
        
        # Get specific frame
        frame = read_storage.get_frame(2)
        assert frame.frame_id == 2
        np.testing.assert_array_almost_equal(frame.body_pose, np.ones((33, 3)) * 2)
        
        read_storage.close()
```

**Step 2: Run test (will fail)**

```bash
pytest tests/unit/test_skeleton_storage.py -v
```

**Step 3: Implement SkeletonStorage**

```python
# agent/ml/skeleton_storage.py
"""
Skeleton Pose Storage - Efficient msgpack-based storage for pose sequences
"""
import msgpack
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class SkeletonFrame:
    """Single frame of skeleton data."""
    frame_id: int
    timestamp: float
    body_pose: Optional[np.ndarray]  # (33, 3) MediaPipe body
    left_hand: Optional[np.ndarray]  # (21, 3)
    right_hand: Optional[np.ndarray]  # (21, 3)
    face: Optional[np.ndarray]  # (468, 3)
    metadata: Optional[Dict[str, Any]] = None


class SkeletonStorage:
    """Efficient storage for pose sequences."""
    
    def __init__(self, base_path: str, name: str, mode: str = 'w', fps: float = 30.0):
        """
        Initialize storage.
        
        Args:
            base_path: Base directory for storage
            name: Pose sequence name (e.g., "wave_left_hand")
            mode: 'w' (write), 'r' (read)
            fps: Frames per second (metadata)
        """
        self.base_path = base_path
        self.name = name
        self.mode = mode
        self.fps = fps
        
        os.makedirs(base_path, exist_ok=True)
        
        self.data_file = os.path.join(base_path, f"{name}.msgpack")
        self.index_file = os.path.join(base_path, f"{name}_index.json")
        self.metadata_file = os.path.join(base_path, f"{name}_metadata.json")
        
        self.frames: Dict[int, SkeletonFrame] = {}
        self.total_frames = 0
        
        if mode == 'r':
            self._load()
    
    def add_frame(self, frame: SkeletonFrame) -> None:
        """Add frame to storage (write mode)."""
        if self.mode != 'w':
            raise ValueError("Storage opened in read mode")
        
        self.frames[frame.frame_id] = frame
        self.total_frames = max(self.total_frames, frame.frame_id + 1)
    
    def get_frame(self, frame_id: int) -> Optional[SkeletonFrame]:
        """Get frame by ID (read mode)."""
        if self.mode != 'r':
            raise ValueError("Storage opened in write mode")
        
        return self.frames.get(frame_id)
    
    def finalize(self) -> None:
        """Write all data to disk (write mode)."""
        if self.mode != 'w':
            raise ValueError("Storage opened in read mode")
        
        self._write_data()
        self._write_index()
        self._write_metadata()
    
    def _write_data(self) -> None:
        """Write pose frames to msgpack."""
        data = {}
        
        for frame_id, frame in self.frames.items():
            frame_data = {
                'frame_id': frame.frame_id,
                'timestamp': frame.timestamp,
                'body': frame.body_pose.tolist() if frame.body_pose is not None else None,
                'left_hand': frame.left_hand.tolist() if frame.left_hand is not None else None,
                'right_hand': frame.right_hand.tolist() if frame.right_hand is not None else None,
                'face': frame.face.tolist() if frame.face is not None else None,
                'metadata': frame.metadata or {}
            }
            data[frame_id] = frame_data
        
        with open(self.data_file, 'wb') as f:
            msgpack.packb(data, use_bin_type=True, f=f)
        
        logger.info(f"Wrote {len(data)} frames to {self.data_file}")
    
    def _write_index(self) -> None:
        """Write frame index for fast lookup."""
        index = {
            'total_frames': self.total_frames,
            'fps': self.fps,
            'frame_ids': list(self.frames.keys()),
            'timestamps': [self.frames[fid].timestamp for fid in sorted(self.frames.keys())]
        }
        
        with open(self.index_file, 'w') as f:
            json.dump(index, f)
    
    def _write_metadata(self) -> None:
        """Write metadata."""
        metadata = {
            'name': self.name,
            'total_frames': self.total_frames,
            'fps': self.fps,
            'duration_sec': self.total_frames / self.fps
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load(self) -> None:
        """Load from disk (read mode)."""
        # Load metadata
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                self.fps = metadata.get('fps', 30.0)
                self.total_frames = metadata.get('total_frames', 0)
        
        # Load data
        if os.path.exists(self.data_file):
            with open(self.data_file, 'rb') as f:
                data = msgpack.unpackb(f.read(), raw=False)
            
            for frame_id, frame_data in data.items():
                frame = SkeletonFrame(
                    frame_id=frame_data['frame_id'],
                    timestamp=frame_data['timestamp'],
                    body_pose=np.array(frame_data['body']) if frame_data['body'] else None,
                    left_hand=np.array(frame_data['left_hand']) if frame_data['left_hand'] else None,
                    right_hand=np.array(frame_data['right_hand']) if frame_data['right_hand'] else None,
                    face=np.array(frame_data['face']) if frame_data['face'] else None,
                    metadata=frame_data.get('metadata')
                )
                self.frames[frame_id] = frame
    
    def close(self) -> None:
        """Cleanup."""
        pass
```

**Step 4-5: Test and commit**

```bash
pytest tests/unit/test_skeleton_storage.py -v
# Expected: PASSED (3 tests)

git add agent/ml/skeleton_storage.py tests/unit/test_skeleton_storage.py
git commit -m "feat(ml): add skeleton pose storage with msgpack"
```

---

## Phase 3: Video Analysis Pipeline

### Task 4: Pose Extraction Pipeline (orchestrates Detector + VideoExtractor)

**Files:**
- Create: `agent/ml/pose_extractor.py`
- Test: `tests/unit/test_pose_extractor.py`

**Overview:** Orchestrates video extraction, pose detection, storage. Single entry point for analyzing video files.

**Step 1: Write failing test**

```python
# tests/unit/test_pose_extractor.py
import pytest
import tempfile
import os
from agent.ml.pose_extractor import PoseExtractor

class TestPoseExtractor:
    def test_extractor_init(self):
        extractor = PoseExtractor()
        assert extractor is not None
        assert hasattr(extractor, 'analyze_video')
    
    def test_analyze_video_integration(self):
        """Integration test: extract poses from dummy video."""
        extractor = PoseExtractor()
        
        # Create dummy video
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            video_path = f.name
        
        os.system(f"ffmpeg -f lavfi -i testsrc=s=320x240:d=0.5 -f lavfi -i sine=f=1000:d=0.5 {video_path} -y -loglevel quiet")
        
        with tempfile.TemporaryDirectory() as output_dir:
            result = extractor.analyze_video(
                video_path=video_path,
                output_dir=output_dir,
                pose_name="test_pose"
            )
            
            assert result['success'] is True
            assert result['total_frames'] > 0
            assert result['detected_frames'] > 0
            assert os.path.exists(result['storage_path'])
        
        os.remove(video_path)
```

**Step 2-5: Implement, test, commit**

```python
# agent/ml/pose_extractor.py
"""
Pose Extraction Pipeline - Orchestrates video analysis and pose storage
"""
import logging
from typing import Dict, Any
from agent.ml.video_extractor import VideoExtractor
from agent.ml.pose_detector import PoseDetector
from agent.ml.skeleton_storage import SkeletonStorage, SkeletonFrame

logger = logging.getLogger(__name__)

class PoseExtractor:
    """Orchestrates video analysis and pose extraction."""
    
    def analyze_video(self, video_path: str, output_dir: str, pose_name: str, skip_frames: int = 1) -> Dict[str, Any]:
        """
        Analyze video and extract poses.
        
        Args:
            video_path: Path to input video
            output_dir: Directory to store results
            pose_name: Name for pose sequence
            skip_frames: Skip every N frames (for efficiency)
            
        Returns:
            Dict with analysis results
        """
        logger.info(f"Analyzing video: {video_path}")
        
        detector = PoseDetector()
        extractor = VideoExtractor(video_path)
        storage = SkeletonStorage(output_dir, pose_name, fps=extractor.fps)
        
        frame_count = 0
        detected_count = 0
        
        try:
            for frame, timestamp in extractor.iterate_frames():
                if frame_count % skip_frames != 0:
                    frame_count += 1
                    continue
                
                pose_result = detector.process_frame(frame)
                
                if pose_result['success']:
                    detected_count += 1
                    
                    frame_data = SkeletonFrame(
                        frame_id=frame_count,
                        timestamp=timestamp,
                        body_pose=pose_result.get('body_landmarks'),
                        left_hand=pose_result.get('hand_landmarks_left'),
                        right_hand=pose_result.get('hand_landmarks_right'),
                        face=pose_result.get('face_landmarks')
                    )
                    storage.add_frame(frame_data)
                
                frame_count += 1
                
                if frame_count % 30 == 0:
                    logger.info(f"Processed {frame_count} frames, detected {detected_count}")
            
            storage.finalize()
            detector.close()
            extractor.close()
            
            return {
                'success': True,
                'total_frames': frame_count,
                'detected_frames': detected_count,
                'detection_rate': detected_count / frame_count if frame_count > 0 else 0,
                'storage_path': output_dir,
                'pose_name': pose_name
            }
        
        except Exception as e:
            logger.error(f"Error analyzing video: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
```

---

## Phase 4: Playback & Integration

### Task 5: Orchestrator Pose Playback Controller

**Files:**
- Create: `agent/output/pose_playback_controller.py`
- Modify: `agent/orchestrator.py` (add pose playback methods)
- Test: `tests/unit/test_pose_playback_controller.py`

**Overview:** Controller in Orchestrator that loads pose sequences and sends playback commands to Frontend via WebSocket.

**Implementation details in Task 5+...**

---

## Phase 5: Frontend Integration (Three.js)

### Task 6: Pose Playback Executor (React/Three.js)

**Files:**
- Create: `web_avatar/src/logic/PosePlayer.js`
- Modify: `web_avatar/src/logic/AvatarStateManager.js` (integrate pose playback)
- Test: `web_avatar/src/__tests__/PosePlayer.test.js`

**Overview:** Receives pose playback commands via WebSocket, applies bone transformations to VRM model in Three.js.

---

## Testing Strategy

- **Unit tests**: Each component tested in isolation (test files above)
- **Integration tests**: Video → Pose → Storage → Playback
- **E2E tests**: Full workflow from video file to VRM animation

## Success Criteria

- ✅ Video analysis extracts poses from sample videos (>70% detection rate)
- ✅ Pose storage uses <50MB for 30sec video @30fps
- ✅ Playback latency <100ms from Orchestrator command to VRM animation
- ✅ Full backward compatibility (expression control still works)
- ✅ All tests passing (100+ new tests)
