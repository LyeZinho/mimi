"""VideoExtractor: Extract frames from video files using FFmpeg piping."""

import logging
import shutil
import subprocess
from typing import Iterator, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VideoExtractor:
    """Extract frames from video files using FFmpeg pipe output.
    
    This class handles video frame extraction by spawning an ffmpeg subprocess
    that outputs raw BGR24 frames to stdout, which are then read as numpy arrays.
    Metadata (fps, total_frames, width, height) is detected via ffprobe.
    """

    def __init__(self, video_path: str, fps_override: Optional[int] = None) -> None:
        """Initialize VideoExtractor with video file path.
        
        Args:
            video_path: Path to video file (any codec ffmpeg supports).
            fps_override: Optional FPS override. If provided, uses this value instead
                         of detected FPS. Useful for custom frame sampling.
        
        Raises:
            FileNotFoundError: If video_path does not exist or ffmpeg/ffprobe not in PATH.
            RuntimeError: If ffprobe fails to detect video metadata.
        """
        self.video_path = video_path
        self._process: Optional[subprocess.Popen] = None
        self._fps_override = fps_override
        
        # Detect video metadata via ffprobe
        self._fps = self._detect_fps()
        self._total_frames = self._detect_frame_count()
        self._width = self._detect_width()
        self._height = self._detect_height()
        
        logger.info(
            f"VideoExtractor initialized: {video_path} "
            f"({self._width}x{self._height}, {self._total_frames} frames, {self._fps} FPS)"
        )

    @property
    def fps(self) -> float:
        """Get frames per second of the video.
        
        Returns:
            FPS as float. If fps_override was provided, returns that value.
        """
        if self._fps_override is not None:
            return float(self._fps_override)
        return self._fps

    @property
    def total_frames(self) -> int:
        """Get total frame count of the video.
        
        Returns:
            Total number of frames in video.
        """
        return self._total_frames

    @property
    def width(self) -> int:
        """Get video width in pixels.
        
        Returns:
            Video width.
        """
        return self._width

    @property
    def height(self) -> int:
        """Get video height in pixels.
        
        Returns:
            Video height.
        """
        return self._height

    def iterate_frames(self) -> Iterator[Tuple[np.ndarray, float]]:
        """Iterate over video frames.
        
        Yields frames as BGR numpy arrays with corresponding timestamps.
        This method spawns an ffmpeg subprocess that outputs raw BGR24 video data.
        
        Yields:
            Tuple of (frame, timestamp) where:
                - frame: BGR numpy array of shape (height, width, 3) with dtype uint8
                - timestamp: float timestamp in seconds since start of video
                
        Raises:
            RuntimeError: If ffmpeg subprocess fails to start or produce output.
        """
        # Spawn ffmpeg subprocess to output raw BGR24 frames
        cmd = [
            "ffmpeg",
            "-i", self.video_path,
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-v", "error",  # Suppress ffmpeg logging
            "pipe:1"
        ]
        
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10 * 1024 * 1024  # 10 MB buffer
            )
        except FileNotFoundError as e:
            logger.error("ffmpeg not found in PATH")
            raise RuntimeError("ffmpeg not found in PATH") from e
        
        frame_size = self._width * self._height * 3  # BGR24 = 3 bytes per pixel
        frame_number = 0
        
        try:
            while True:
                # Read one frame from ffmpeg stdout
                if self._process is None or self._process.stdout is None:
                    break
                frame_data = self._process.stdout.read(frame_size)
                
                if len(frame_data) < frame_size:
                    # EOF reached
                    break
                
                # Convert raw bytes to numpy array
                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape(
                    self._height, self._width, 3
                )
                
                # Calculate timestamp in seconds
                timestamp = frame_number / self.fps
                
                yield frame, timestamp
                frame_number += 1
        finally:
            # Ensure subprocess is cleaned up
            self.close()

    def close(self) -> None:
        """Close video extractor and terminate ffmpeg subprocess.
        
        Safely terminates the ffmpeg subprocess if it's running.
        Safe to call multiple times.
        """
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except (subprocess.TimeoutExpired, Exception) as e:
                logger.warning(f"Error terminating ffmpeg subprocess: {e}")
                try:
                    self._process.kill()
                except Exception:
                    pass
            finally:
                self._process = None
            
            logger.info(f"VideoExtractor closed for {self.video_path}")

    def _detect_fps(self) -> float:
        """Detect FPS of video using ffprobe.
        
        Returns:
            FPS as float. If fps_override was provided, this value is ignored
            in the fps property but stored here for reference.
        
        Raises:
            RuntimeError: If ffprobe fails or cannot detect FPS.
        """
        if self._fps_override is not None:
            return float(self._fps_override)
        
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=r_frame_rate",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_section=1",
            self.video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            # Parse fps format like "30/1" or "60000/1001"
            fps_str = result.stdout.strip()
            if "/" in fps_str:
                numerator, denominator = fps_str.split("/")
                fps = float(numerator) / float(denominator)
            else:
                fps = float(fps_str)
            
            return fps
        except (subprocess.TimeoutExpired, ValueError) as e:
            logger.error(f"Failed to detect FPS: {e}")
            raise RuntimeError(f"Failed to detect FPS: {e}") from e

    def _detect_frame_count(self) -> int:
        """Detect total frame count using ffprobe -count_packets.
        
        Returns:
            Total number of frames in video.
        
        Raises:
            RuntimeError: If ffprobe fails or cannot detect frame count.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_section=1",
            self.video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            frame_count_str = result.stdout.strip()
            frame_count = int(frame_count_str)
            
            return frame_count
        except (subprocess.TimeoutExpired, ValueError) as e:
            logger.error(f"Failed to detect frame count: {e}")
            raise RuntimeError(f"Failed to detect frame count: {e}") from e

    def _detect_width(self) -> int:
        """Detect video width using ffprobe.
        
        Returns:
            Video width in pixels.
        
        Raises:
            RuntimeError: If ffprobe fails or cannot detect width.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_section=1",
            self.video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            width = int(result.stdout.strip())
            return width
        except (subprocess.TimeoutExpired, ValueError) as e:
            logger.error(f"Failed to detect width: {e}")
            raise RuntimeError(f"Failed to detect width: {e}") from e

    def _detect_height(self) -> int:
        """Detect video height using ffprobe.
        
        Returns:
            Video height in pixels.
        
        Raises:
            RuntimeError: If ffprobe fails or cannot detect height.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=height",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_section=1",
            self.video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"ffprobe failed: {result.stderr}")
            
            height = int(result.stdout.strip())
            return height
        except (subprocess.TimeoutExpired, ValueError) as e:
            logger.error(f"Failed to detect height: {e}")
            raise RuntimeError(f"Failed to detect height: {e}") from e
