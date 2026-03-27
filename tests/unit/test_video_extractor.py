"""Unit tests for VideoExtractor FFmpeg-based video frame extraction."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator, Tuple

import numpy as np
import pytest

# Skip all tests if FFmpeg is unavailable
ffmpeg_available = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
pytestmark = pytest.mark.skipif(not ffmpeg_available, reason="FFmpeg and ffprobe not available")

from agent.ml.video_extractor import VideoExtractor


class TestVideoExtractorInit:
    """Tests for VideoExtractor initialization and metadata detection."""

    @pytest.fixture
    def dummy_video_path(self, tmp_path: Path) -> str:
        """Create a test video file using FFmpeg testsrc filter.
        
        Creates a 1-second video at 30 FPS with 320x240 resolution.
        Uses the testsrc filter to generate a test pattern (no input file needed).
        
        Args:
            tmp_path: pytest temporary directory.
            
        Returns:
            Path to the generated video file as a string.
        """
        video_file = tmp_path / "test_video.mp4"
        
        # Create 1-second test video at 30 FPS, 320x240 resolution
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=s=320x240:d=1",  # testsrc filter: 1 second, 320x240
            "-pix_fmt", "yuv420p",
            "-y",  # Overwrite output
            str(video_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"Failed to create test video: {result.stderr}")
        
        assert video_file.exists(), f"Test video not created: {video_file}"
        return str(video_file)

    def test_extractor_init_detects_fps(self, dummy_video_path: str) -> None:
        """Test that VideoExtractor correctly detects FPS from video metadata.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        # testsrc runs at 25 FPS by default, but we should detect it
        assert extractor.fps > 0, "FPS should be positive"
        assert isinstance(extractor.fps, (int, float)), "FPS should be numeric"
        
        extractor.close()

    def test_extractor_init_detects_total_frames(self, dummy_video_path: str) -> None:
        """Test that VideoExtractor correctly detects total frame count.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        # 1-second video should have ~25-30 frames depending on FPS
        assert extractor.total_frames > 0, "Total frames should be positive"
        assert extractor.total_frames >= 20, "1-second video should have at least 20 frames"
        
        extractor.close()

    def test_extractor_init_detects_resolution(self, dummy_video_path: str) -> None:
        """Test that VideoExtractor correctly detects video resolution.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        # testsrc creates 320x240 video
        assert extractor.width == 320, f"Expected width 320, got {extractor.width}"
        assert extractor.height == 240, f"Expected height 240, got {extractor.height}"
        
        extractor.close()

    def test_extractor_with_fps_override(self, dummy_video_path: str) -> None:
        """Test that VideoExtractor respects fps_override parameter.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        fps_override = 10
        extractor = VideoExtractor(dummy_video_path, fps_override=fps_override)
        
        assert extractor.fps == fps_override, f"Expected fps {fps_override}, got {extractor.fps}"
        
        extractor.close()


class TestVideoExtractorIterateFrames:
    """Tests for VideoExtractor frame iteration functionality."""

    @pytest.fixture
    def dummy_video_path(self, tmp_path: Path) -> str:
        """Create a test video file using FFmpeg testsrc filter.
        
        Creates a 1-second video at 30 FPS with 320x240 resolution.
        
        Args:
            tmp_path: pytest temporary directory.
            
        Returns:
            Path to the generated video file as a string.
        """
        video_file = tmp_path / "test_video.mp4"
        
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=s=320x240:d=1",
            "-pix_fmt", "yuv420p",
            "-y",
            str(video_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"Failed to create test video: {result.stderr}")
        
        assert video_file.exists()
        return str(video_file)

    def test_iterate_frames_returns_iterator(self, dummy_video_path: str) -> None:
        """Test that iterate_frames() returns an iterator.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        frames_iter = extractor.iterate_frames()
        
        assert hasattr(frames_iter, "__iter__"), "iterate_frames should return an iterator"
        assert hasattr(frames_iter, "__next__"), "iterate_frames should support __next__"
        
        extractor.close()

    def test_iterate_frames_yields_correct_shape(self, dummy_video_path: str) -> None:
        """Test that each frame has correct shape (H, W, 3) in BGR format.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        frame_count = 0
        for frame, timestamp in extractor.iterate_frames():
            frame_count += 1
            
            # Verify frame is numpy array
            assert isinstance(frame, np.ndarray), "Frame should be numpy array"
            
            # Verify shape is (H, W, 3)
            assert len(frame.shape) == 3, f"Frame should have 3 dimensions, got {len(frame.shape)}"
            assert frame.shape[2] == 3, f"Frame should have 3 channels (BGR), got {frame.shape[2]}"
            
            # Verify resolution matches
            assert frame.shape[0] == 240, f"Expected height 240, got {frame.shape[0]}"
            assert frame.shape[1] == 320, f"Expected width 320, got {frame.shape[1]}"
            
            # Verify dtype is uint8
            assert frame.dtype == np.uint8, f"Frame dtype should be uint8, got {frame.dtype}"
            
            # Only check first frame for speed
            break
        
        assert frame_count > 0, "Should have extracted at least one frame"
        extractor.close()

    def test_iterate_frames_yields_timestamps(self, dummy_video_path: str) -> None:
        """Test that timestamps are monotonically increasing and in seconds.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        previous_timestamp = -1.0
        frame_count = 0
        
        for frame, timestamp in extractor.iterate_frames():
            frame_count += 1
            
            # Verify timestamp is float
            assert isinstance(timestamp, float), "Timestamp should be float"
            
            # Verify timestamp is non-negative
            assert timestamp >= 0.0, f"Timestamp should be non-negative, got {timestamp}"
            
            # Verify timestamps are monotonically increasing
            assert timestamp >= previous_timestamp, \
                f"Timestamps should be monotonically increasing, got {timestamp} after {previous_timestamp}"
            
            previous_timestamp = timestamp
        
        assert frame_count > 0, "Should have extracted at least one frame"
        extractor.close()

    def test_iterate_frames_extracts_all_frames(self, dummy_video_path: str) -> None:
        """Test that iterate_frames() extracts all frames from video.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        frame_count = 0
        for frame, timestamp in extractor.iterate_frames():
            frame_count += 1
        
        # Should extract all frames (allow ±2 for rounding differences)
        assert frame_count > 0, "Should extract at least one frame"
        assert abs(frame_count - extractor.total_frames) <= 2, \
            f"Extracted {frame_count} frames but total_frames reported {extractor.total_frames}"
        
        extractor.close()


class TestVideoExtractorClose:
    """Tests for VideoExtractor resource cleanup."""

    @pytest.fixture
    def dummy_video_path(self, tmp_path: Path) -> str:
        """Create a test video file using FFmpeg testsrc filter.
        
        Args:
            tmp_path: pytest temporary directory.
            
        Returns:
            Path to the generated video file as a string.
        """
        video_file = tmp_path / "test_video.mp4"
        
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=s=320x240:d=1",
            "-pix_fmt", "yuv420p",
            "-y",
            str(video_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip(f"Failed to create test video: {result.stderr}")
        
        return str(video_file)

    def test_close_terminates_subprocess(self, dummy_video_path: str) -> None:
        """Test that close() properly terminates the ffmpeg subprocess.
        
        Args:
            dummy_video_path: Path to test video fixture.
        """
        extractor = VideoExtractor(dummy_video_path)
        
        # Start iteration (which launches ffmpeg subprocess)
        frames_iter = extractor.iterate_frames()
        next(frames_iter)
        
        # close() should terminate subprocess
        extractor.close()
        
        # Verify subprocess is None after close
        assert extractor._process is None, "Subprocess should be None after close()"
