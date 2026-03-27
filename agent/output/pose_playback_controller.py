"""PosePlaybackController: Orchestrates pose sequence playback to frontend via WebSocket.

Reads pose data from SkeletonStorage and publishes POSE_PLAYBACK events through EventBus,
enabling the frontend to apply poses to VRM avatar bones in real-time.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

from agent.core.messaging import EventBus, SharedAgentState, AgentEvent, EventType
from agent.ml.skeleton_storage import SkeletonStorage

logger = logging.getLogger(__name__)


class PosePlaybackController:
    """Controls pose playback from stored sequences to frontend avatar.
    
    Responsibilities:
    - Load pose sequences from SkeletonStorage
    - Emit pose frames to frontend via EventBus
    - Track playback state (current frame, is_playing)
    - Validate frame existence before playback
    """

    def __init__(self, event_bus: EventBus, shared_state: SharedAgentState) -> None:
        """Initialize PosePlaybackController.
        
        Args:
            event_bus: EventBus instance for emitting events to frontend
            shared_state: SharedAgentState for system coordination
        """
        self.event_bus = event_bus
        self.shared_state = shared_state
        self.loaded_poses: Optional[SkeletonStorage] = None
        self.is_playing = False
        self.current_frame_id = -1
        self.logger = logging.getLogger(__name__)
        
        logger.info("PosePlaybackController initialized")

    def load_pose_sequence(self, storage_path: str, pose_name: str) -> bool:
        """Load pose sequence from storage directory.
        
        Args:
            storage_path: Directory path containing pose files
            pose_name: Name prefix of pose files (e.g., 'sequence' for sequence.msgpack)
            
        Returns:
            bool: True if sequence loaded successfully, False otherwise
        """
        try:
            storage = SkeletonStorage(
                base_path=Path(storage_path),
                name=pose_name,
                mode="r"
            )
            
            if storage.total_frames == 0:
                logger.warning(f"Loaded storage has 0 frames: {pose_name}")
                return False
            
            self.loaded_poses = storage
            self.current_frame_id = -1
            
            logger.info(f"Loaded pose sequence: {pose_name} with {storage.total_frames} frames")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load pose sequence {pose_name}: {e}")
            return False

    def play_pose(self, frame_id: int, fade_duration: float = 0.0) -> Dict[str, Any]:
        """Play a specific pose frame to frontend.
        
        Validates frame exists, retrieves pose data, and publishes POSE_PLAYBACK event
        with pose data in JSON-serializable format.
        
        Args:
            frame_id: Frame ID to play
            fade_duration: Transition duration in seconds (default: 0.0 for instant)
            
        Returns:
            Dict with success status and metadata, or error dict if frame not found
        """
        if self.loaded_poses is None:
            logger.warning("No pose sequence loaded, cannot play frame")
            return {"success": False, "error": "No sequence loaded"}
        
        frame = self.loaded_poses.get_frame(frame_id)
        if frame is None:
            logger.warning(f"Frame {frame_id} not found in loaded sequence")
            return {"success": False, "error": f"Frame {frame_id} not found"}
        
        try:
            timestamp = frame.timestamp
            
            pose_data = {
                "body": frame.body_pose.tolist(),
                "left_hand": frame.left_hand.tolist() if frame.left_hand is not None else None,
                "right_hand": frame.right_hand.tolist() if frame.right_hand is not None else None,
                "face": frame.face.tolist() if frame.face is not None else None
            }
            
            event_payload = {
                "action": "play_pose",
                "frame_id": frame_id,
                "timestamp": timestamp,
                "fade_duration": fade_duration,
                "pose_data": pose_data
            }
            
            event = AgentEvent(
                type=EventType.POSE_PLAYBACK,
                source_brain="orchestrator",
                payload=event_payload
            )
            
            if hasattr(self.event_bus, 'emit'):
                self.event_bus.emit(EventType.POSE_PLAYBACK, event_payload)
            else:
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(self.event_bus.publish(event))
                except RuntimeError:
                    logger.debug("No async loop available for publishing event")
            
            self.current_frame_id = frame_id
            logger.debug(f"Played pose frame {frame_id} (timestamp: {timestamp:.3f}s)")
            
            return {
                "success": True,
                "frame_id": frame_id,
                "timestamp": timestamp,
                "fade_duration": fade_duration
            }
        
        except Exception as e:
            logger.error(f"Error playing frame {frame_id}: {e}")
            return {"success": False, "error": str(e)}

    def start_sequence_playback(self, sequence_config: Dict[str, Any]) -> bool:
        """Start playback of a pose sequence.
        
        MVP implementation validates config structure. Full implementation would
        handle frame-by-frame playback with loop/speed control.
        
        Args:
            sequence_config: Configuration dict with keys:
                - start_frame: int, starting frame ID
                - end_frame: int, ending frame ID
                - loop: bool, whether to loop sequence
                - speed: float, playback speed multiplier
                
        Returns:
            bool: True if config valid and playback started, False otherwise
        """
        try:
            required_keys = {"start_frame", "end_frame", "loop", "speed"}
            if not all(key in sequence_config for key in required_keys):
                logger.warning(f"Invalid sequence config, missing keys: {required_keys - set(sequence_config.keys())}")
                return False
            
            self.is_playing = True
            logger.info(f"Started sequence playback: {sequence_config}")
            return True
        
        except Exception as e:
            logger.error(f"Error starting sequence playback: {e}")
            return False

    def stop_playback(self) -> None:
        """Stop current pose playback.
        
        Sets is_playing flag to False and resets playback state.
        """
        self.is_playing = False
        self.current_frame_id = -1
        logger.info("Stopped pose playback")
