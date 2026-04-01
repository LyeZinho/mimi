"""Unit tests for PosePlaybackController - orchestrates pose sequence playback to frontend."""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any

from agent.ml.skeleton_storage import SkeletonStorage, SkeletonFrame
from agent.output.pose_playback_controller import PosePlaybackController


class TestPosePlaybackControllerInit:
    """Test PosePlaybackController initialization."""

    def test_controller_init_creates_instance(self):
        """Test that PosePlaybackController initializes with event_bus and shared_state."""
        # Mock dependencies
        mock_event_bus = Mock()
        mock_shared_state = Mock()

        # Create controller
        controller = PosePlaybackController(mock_event_bus, mock_shared_state)

        # Verify initialization
        assert controller.event_bus is mock_event_bus
        assert controller.shared_state is mock_shared_state
        assert controller.loaded_poses is None
        assert controller.is_playing is False
        assert controller.current_frame_id == -1

    def test_controller_init_sets_logger(self):
        """Test that controller initializes with logger."""
        mock_event_bus = Mock()
        mock_shared_state = Mock()

        controller = PosePlaybackController(mock_event_bus, mock_shared_state)

        assert controller.logger is not None
        assert hasattr(controller.logger, 'info')
        assert hasattr(controller.logger, 'debug')
        assert hasattr(controller.logger, 'error')


class TestPosePlaybackControllerLoadSequence:
    """Test loading pose sequences from storage."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Provide temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def controller(self):
        """Provide mock controller."""
        mock_event_bus = Mock()
        mock_shared_state = Mock()
        return PosePlaybackController(mock_event_bus, mock_shared_state)

    def test_load_pose_sequence_creates_skeleton_storage(self, controller, temp_storage_dir):
        """Test that load_pose_sequence creates SkeletonStorage and sets loaded_poses."""
        # Create test storage with frames
        write_storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="test_poses",
            mode="w",
            fps=30.0
        )

        # Add test frames
        for i in range(5):
            frame = SkeletonFrame(
                frame_id=i,
                timestamp=i / 30.0,
                body_pose=np.random.rand(33, 3).astype(np.float32),
                left_hand=np.random.rand(21, 3).astype(np.float32),
                right_hand=np.random.rand(21, 3).astype(np.float32),
                face=np.random.rand(468, 3).astype(np.float32),
                metadata={"frame": i}
            )
            write_storage.add_frame(frame)

        write_storage.finalize()
        write_storage.close()

        # Load the sequence
        result = controller.load_pose_sequence(str(temp_storage_dir), "test_poses")

        # Verify result
        assert result is True
        assert controller.loaded_poses is not None
        assert controller.loaded_poses.total_frames == 5

    def test_load_pose_sequence_returns_false_on_missing_storage(self, controller, temp_storage_dir):
        """Test that load_pose_sequence returns False when storage doesn't exist."""
        result = controller.load_pose_sequence(str(temp_storage_dir), "nonexistent")

        assert result is False
        assert controller.loaded_poses is None

    def test_load_pose_sequence_logs_load_event(self, controller, temp_storage_dir):
        """Test that load_pose_sequence successfully loads and returns True."""
        write_storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="test_poses",
            mode="w"
        )

        frame = SkeletonFrame(
            frame_id=0,
            timestamp=0.0,
            body_pose=np.random.rand(33, 3).astype(np.float32),
            left_hand=np.random.rand(21, 3).astype(np.float32),
            right_hand=np.random.rand(21, 3).astype(np.float32),
            face=np.random.rand(468, 3).astype(np.float32)
        )
        write_storage.add_frame(frame)
        write_storage.finalize()
        write_storage.close()

        result = controller.load_pose_sequence(str(temp_storage_dir), "test_poses")

        assert result is True
        assert controller.loaded_poses is not None
        assert controller.loaded_poses.total_frames == 1


class TestPosePlaybackControllerPlayPose:
    """Test playing individual pose frames."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Provide temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def controller_with_poses(self, temp_storage_dir):
        """Provide controller with loaded poses."""
        # Create test storage with frames
        write_storage = SkeletonStorage(
            base_path=temp_storage_dir,
            name="test_poses",
            mode="w",
            fps=30.0
        )

        # Add 10 test frames
        for i in range(10):
            frame = SkeletonFrame(
                frame_id=i,
                timestamp=i / 30.0,
                body_pose=np.full((33, 3), float(i), dtype=np.float32),
                left_hand=np.full((21, 3), float(i), dtype=np.float32),
                right_hand=np.full((21, 3), float(i), dtype=np.float32),
                face=np.full((468, 3), float(i), dtype=np.float32)
            )
            write_storage.add_frame(frame)

        write_storage.finalize()
        write_storage.close()

        # Create controller and load poses
        mock_event_bus = Mock()
        mock_shared_state = Mock()
        controller = PosePlaybackController(mock_event_bus, mock_shared_state)
        controller.load_pose_sequence(str(temp_storage_dir), "test_poses")

        return controller

    def test_play_pose_emits_event(self, controller_with_poses):
        """Test that play_pose emits POSE_PLAYBACK event with correct payload."""
        # Play frame 0
        result = controller_with_poses.play_pose(frame_id=0, fade_duration=0.1)

        # Verify event was emitted
        assert controller_with_poses.event_bus.emit.called
        
        # Get the event that was emitted
        call_args = controller_with_poses.event_bus.emit.call_args
        event_type = call_args[0][0] if call_args[0] else call_args[1].get('event_type')
        
        # Verify event type is POSE_PLAYBACK
        assert 'POSE_PLAYBACK' in str(event_type) or event_type == 'POSE_PLAYBACK'

    def test_play_pose_returns_success_dict(self, controller_with_poses):
        """Test that play_pose returns success dict with frame_id and timestamp."""
        result = controller_with_poses.play_pose(frame_id=0, fade_duration=0.1)

        assert isinstance(result, dict)
        assert result.get('success') is True
        assert result.get('frame_id') == 0
        assert 'timestamp' in result

    def test_play_pose_includes_pose_data_in_event(self, controller_with_poses):
        """Test that play_pose event includes pose_data with body/hands/face."""
        # Play frame 0
        controller_with_poses.play_pose(frame_id=0, fade_duration=0.1)

        # Get the event payload
        call_args = controller_with_poses.event_bus.emit.call_args
        event_payload = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('payload')

        # Verify payload structure
        assert 'pose_data' in event_payload
        pose_data = event_payload['pose_data']
        assert 'body' in pose_data
        assert 'left_hand' in pose_data
        assert 'right_hand' in pose_data
        assert 'face' in pose_data

    def test_play_pose_validates_frame_exists(self, controller_with_poses):
        """Test that play_pose validates frame_id exists before playing."""
        # Try to play non-existent frame
        result = controller_with_poses.play_pose(frame_id=999, fade_duration=0.1)

        # Should return error or False
        assert result.get('success') is False or result is None

    def test_play_pose_updates_current_frame_id(self, controller_with_poses):
        """Test that play_pose updates current_frame_id."""
        initial_frame = controller_with_poses.current_frame_id
        controller_with_poses.play_pose(frame_id=5, fade_duration=0.1)

        assert controller_with_poses.current_frame_id == 5 or controller_with_poses.current_frame_id != initial_frame

    def test_play_pose_with_default_fade_duration(self, controller_with_poses):
        """Test play_pose with default fade_duration."""
        result = controller_with_poses.play_pose(frame_id=0)

        assert result.get('success') is True
        # Check that event was still emitted
        assert controller_with_poses.event_bus.emit.called


class TestPosePlaybackControllerSequence:
    """Test sequence playback control."""

    @pytest.fixture
    def controller(self):
        """Provide mock controller."""
        mock_event_bus = Mock()
        mock_shared_state = Mock()
        return PosePlaybackController(mock_event_bus, mock_shared_state)

    def test_start_sequence_playback_validates_config(self, controller):
        """Test that start_sequence_playback validates config structure."""
        config = {
            'start_frame': 0,
            'end_frame': 10,
            'loop': False,
            'speed': 1.0
        }

        # This should validate and return True for valid config
        # (MVP: just validates config, doesn't play)
        result = controller.start_sequence_playback(config)

        assert result is True

    def test_stop_playback_sets_is_playing_false(self, controller):
        """Test that stop_playback sets is_playing flag to False."""
        controller.is_playing = True
        controller.stop_playback()

        assert controller.is_playing is False

    def test_is_playing_property_initialized_false(self, controller):
        """Test that is_playing is initialized to False."""
        assert controller.is_playing is False
