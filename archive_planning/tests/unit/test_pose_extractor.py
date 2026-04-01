"""Tests for PoseExtractor: video analysis pipeline integration."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pytest

logger = logging.getLogger(__name__)


class TestPoseExtractorInit:
    """Test PoseExtractor initialization."""

    def test_extractor_init(self) -> None:
        """Test that PoseExtractor can be instantiated with analyze_video method."""
        from agent.ml import PoseExtractor

        extractor = PoseExtractor()
        assert extractor is not None
        assert hasattr(extractor, "analyze_video")
        assert callable(extractor.analyze_video)


class TestPoseExtractorIntegration:
    """Test PoseExtractor pipeline integration."""

    @pytest.fixture
    def test_video_file(self, tmp_path: Path) -> Path:
        """Create a dummy test video using FFmpeg testsrc."""
        video_path = tmp_path / "test_video.mp4"
        
        # Create 30 frames of test video (1 second at 30fps)
        cmd = [
            "ffmpeg",
            "-f", "lavfi",
            "-i", "testsrc=s=640x480:d=1",
            "-pix_fmt", "yuv420p",
            "-y",
            str(video_path),
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            pytest.skip(f"FFmpeg not available or testsrc failed: {e}")
        
        assert video_path.exists(), f"Test video not created at {video_path}"
        return video_path

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create a temporary output directory."""
        output = tmp_path / "output"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_analyze_video_integration(
        self, test_video_file: Path, output_dir: Path
    ) -> None:
        """Test that analyze_video processes a test video and returns valid results."""
        from agent.ml import PoseExtractor

        extractor = PoseExtractor()
        
        result = extractor.analyze_video(
            video_path=str(test_video_file),
            output_dir=str(output_dir),
            pose_name="test_pose",
            skip_frames=1,
        )
        
        # Verify result structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "success" in result, "Result must have 'success' key"
        assert result["success"] is True, f"Analysis should succeed. Result: {result}"
        
        # Verify result fields
        assert "total_frames" in result
        assert "detected_frames" in result
        assert "detection_rate" in result
        assert "storage_path" in result
        assert "pose_name" in result
        
        # Verify field types and values
        assert isinstance(result["total_frames"], int), "total_frames must be int"
        assert isinstance(result["detected_frames"], int), "detected_frames must be int"
        assert isinstance(result["detection_rate"], float), "detection_rate must be float"
        assert isinstance(result["storage_path"], str), "storage_path must be str"
        
        # Verify ranges
        assert result["total_frames"] > 0, "Should process at least one frame"
        assert result["detected_frames"] >= 0, "detected_frames must be >= 0"
        assert 0.0 <= result["detection_rate"] <= 1.0, "detection_rate must be 0.0-1.0"
        assert result["pose_name"] == "test_pose"
        
        # Verify storage was created
        assert Path(result["storage_path"]).exists(), "Storage directory should exist"

    def test_analyze_video_error_handling(self, output_dir: Path) -> None:
        """Test that analyze_video handles invalid video paths gracefully."""
        from agent.ml import PoseExtractor

        extractor = PoseExtractor()
        
        result = extractor.analyze_video(
            video_path="/nonexistent/video.mp4",
            output_dir=str(output_dir),
            pose_name="test_pose",
        )
        
        # Should return error dict, not raise exception
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert isinstance(result["error"], str)
