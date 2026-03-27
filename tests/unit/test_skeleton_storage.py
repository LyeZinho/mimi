"""Unit tests for SkeletonStorage module - msgpack-based skeleton pose storage."""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path
from typing import Optional

# These imports will fail until we implement the module (RED phase)
from agent.ml.skeleton_storage import SkeletonStorage, SkeletonFrame


class TestSkeletonFrameCreation:
    """Test SkeletonFrame dataclass creation and properties."""

    def test_skeleton_frame_creation_with_numpy_arrays(self):
        """Test creating SkeletonFrame with numpy arrays for pose data."""
        # Create random pose data
        body_pose = np.random.rand(33, 3).astype(np.float32)
        left_hand = np.random.rand(21, 3).astype(np.float32)
        right_hand = np.random.rand(21, 3).astype(np.float32)
        face = np.random.rand(468, 3).astype(np.float32)

        # Create frame
        frame = SkeletonFrame(
            frame_id=0,
            timestamp=0.0,
            body_pose=body_pose,
            left_hand=left_hand,
            right_hand=right_hand,
            face=face,
            metadata={"test": "value"}
        )

        # Verify properties
        assert frame.frame_id == 0
        assert frame.timestamp == 0.0
        assert frame.body_pose.shape == (33, 3)
        assert frame.left_hand.shape == (21, 3)
        assert frame.right_hand.shape == (21, 3)
        assert frame.face.shape == (468, 3)
        assert frame.metadata == {"test": "value"}

    def test_skeleton_frame_with_optional_metadata(self):
        """Test SkeletonFrame creation with optional metadata."""
        body_pose = np.random.rand(33, 3).astype(np.float32)
        left_hand = np.random.rand(21, 3).astype(np.float32)
        right_hand = np.random.rand(21, 3).astype(np.float32)
        face = np.random.rand(468, 3).astype(np.float32)

        # Create frame without metadata
        frame = SkeletonFrame(
            frame_id=1,
            timestamp=1.5,
            body_pose=body_pose,
            left_hand=left_hand,
            right_hand=right_hand,
            face=face
        )

        # Metadata should default to None or empty dict
        assert frame.metadata is None or frame.metadata == {}


class TestSkeletonStorageWriteAndRead:
    """Test SkeletonStorage write and read operations."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Provide temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_storage_write_and_read_multiple_frames(self, temp_storage_dir):
        """Test writing 5 frames, finalizing, and reading back with data integrity."""
        # Create storage in write mode
        storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="test_sequence",
            mode="w",
            fps=30.0
        )

        # Create and add 5 frames
        frames_data = []
        for i in range(5):
            body_pose = np.array([
                [i + 0.1, i + 0.2, i + 0.3],
                [i + 0.4, i + 0.5, i + 0.6],
                [i + 0.7, i + 0.8, i + 0.9],
            ] + [[i + 0.1 + j*0.01, i + 0.2 + j*0.01, i + 0.3 + j*0.01] for j in range(30)], dtype=np.float32)
            
            left_hand = np.full((21, 3), i * 0.1, dtype=np.float32)
            right_hand = np.full((21, 3), i * 0.2, dtype=np.float32)
            face = np.full((468, 3), i * 0.3, dtype=np.float32)

            frame = SkeletonFrame(
                frame_id=i,
                timestamp=i / 30.0,
                body_pose=body_pose,
                left_hand=left_hand,
                right_hand=right_hand,
                face=face,
                metadata={"frame_index": i}
            )
            storage.add_frame(frame)
            frames_data.append((body_pose, left_hand, right_hand, face))

        # Finalize storage
        storage.finalize()
        storage.close()

        # Verify files were created
        msgpack_file = temp_storage_dir / "test_sequence.msgpack"
        index_file = temp_storage_dir / "test_sequence_index.json"
        metadata_file = temp_storage_dir / "test_sequence_metadata.json"

        assert msgpack_file.exists(), "msgpack file not created"
        assert index_file.exists(), "index file not created"
        assert metadata_file.exists(), "metadata file not created"

        # Read back in read mode
        storage_read = SkeletonStorage(
            base_path=temp_storage_dir,
            name="test_sequence",
            mode="r"
        )

        # Verify metadata
        assert storage_read.total_frames == 5
        assert storage_read.fps == 30.0

        # Verify frames can be read
        for i in range(5):
            frame = storage_read.get_frame(i)
            assert frame is not None
            assert frame.frame_id == i
            assert frame.timestamp == pytest.approx(i / 30.0)
            
            # Verify pose data (with small tolerance for floating point)
            assert frame.body_pose.shape == (33, 3)
            assert frame.left_hand.shape == (21, 3)
            assert frame.right_hand.shape == (21, 3)
            assert frame.face.shape == (468, 3)

        storage_read.close()

    def test_get_frame_returns_exact_values(self, temp_storage_dir):
        """Test that get_frame returns exact values that were stored."""
        storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="exact_test",
            mode="w",
            fps=24.0
        )

        # Create specific test frame with known values
        test_values = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float32)
        body_pose = np.tile(test_values, (17, 1))  # 34 rows (17*2)
        left_hand = np.ones((21, 3), dtype=np.float32) * 10.5
        right_hand = np.ones((21, 3), dtype=np.float32) * 20.5
        face = np.ones((468, 3), dtype=np.float32) * 30.5

        frame = SkeletonFrame(
            frame_id=42,
            timestamp=1.75,
            body_pose=body_pose,
            left_hand=left_hand,
            right_hand=right_hand,
            face=face,
            metadata={"test": "exact"}
        )

        storage.add_frame(frame)
        storage.finalize()
        storage.close()

        # Read back and verify exact values
        storage_read = SkeletonStorage(
            base_path=temp_storage_dir,
            name="exact_test",
            mode="r"
        )

        retrieved_frame = storage_read.get_frame(42)
        assert retrieved_frame is not None
        assert retrieved_frame.frame_id == 42
        assert retrieved_frame.timestamp == pytest.approx(1.75)
        
        # Check exact values with tolerance
        np.testing.assert_array_almost_equal(
            retrieved_frame.body_pose[:2],
            test_values,
            decimal=5
        )
        np.testing.assert_array_almost_equal(
            retrieved_frame.left_hand,
            left_hand,
            decimal=5
        )

        storage_read.close()

    def test_storage_mode_write_only(self, temp_storage_dir):
        """Test that write mode prevents read operations."""
        storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="mode_test",
            mode="w"
        )

        # get_frame should raise or return None in write mode
        result = storage.get_frame(0)
        assert result is None or isinstance(result, type(None))

        storage.close()

    def test_storage_mode_read_only(self, temp_storage_dir):
        """Test that read mode prevents add_frame operations."""
        # First, create a file to read
        storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="read_only_test",
            mode="w"
        )
        frame = SkeletonFrame(
            frame_id=0,
            timestamp=0.0,
            body_pose=np.zeros((33, 3), dtype=np.float32),
            left_hand=np.zeros((21, 3), dtype=np.float32),
            right_hand=np.zeros((21, 3), dtype=np.float32),
            face=np.zeros((468, 3), dtype=np.float32)
        )
        storage.add_frame(frame)
        storage.finalize()
        storage.close()

        # Now try to read
        storage_read = SkeletonStorage(
            base_path=temp_storage_dir,
            name="read_only_test",
            mode="r"
        )

        # add_frame should raise ValueError in read mode
        with pytest.raises(ValueError, match="Cannot add frames in read mode"):
            new_frame = SkeletonFrame(
                frame_id=1,
                timestamp=1.0,
                body_pose=np.zeros((33, 3), dtype=np.float32),
                left_hand=np.zeros((21, 3), dtype=np.float32),
                right_hand=np.zeros((21, 3), dtype=np.float32),
                face=np.zeros((468, 3), dtype=np.float32)
            )
            storage_read.add_frame(new_frame)

        storage_read.close()

    def test_get_nonexistent_frame_returns_none(self, temp_storage_dir):
        """Test that getting a non-existent frame returns None."""
        storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="nonexistent_test",
            mode="w"
        )
        frame = SkeletonFrame(
            frame_id=0,
            timestamp=0.0,
            body_pose=np.zeros((33, 3), dtype=np.float32),
            left_hand=np.zeros((21, 3), dtype=np.float32),
            right_hand=np.zeros((21, 3), dtype=np.float32),
            face=np.zeros((468, 3), dtype=np.float32)
        )
        storage.add_frame(frame)
        storage.finalize()
        storage.close()

        storage_read = SkeletonStorage(
            base_path=temp_storage_dir,
            name="nonexistent_test",
            mode="r"
        )

        result = storage_read.get_frame(999)
        assert result is None

        storage_read.close()
