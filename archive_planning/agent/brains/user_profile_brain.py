"""User Profile Brain - Analyzes long-term memory and builds personality profiles."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from agent.core.messaging import Brain, EventType
from agent.core.user_profile_manager import UserProfileManager

logger = logging.getLogger(__name__)


class UserProfileBrain(Brain):
    """Brain that maintains and updates user personality profiles from Layer 4 memory."""
    
    def __init__(self, data_dir: str | Path = "data", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self._profile_manager = UserProfileManager(
            db_path=self.data_dir / "long_term_memory.db",
            profile_path=self.data_dir / "user_profile.json",
        )
        
        self._analysis_interval = 10
        self._turns_since_analysis = 0
    
    async def initialize(self) -> None:
        """Initialize UserProfileBrain and subscribe to events."""
        await super().initialize()
        
        bus = self.event_bus
        bus.subscribe(EventType.RESPONSE_READY)(self._on_response_ready)
        
        logger.info("UserProfileBrain initialized")
    
    async def process(self) -> None:
        """Background processing - update profile periodically."""
        await self._update_profile_if_needed()
    
    async def _on_response_ready(self, event) -> None:
        """Handle response ready event - potentially trigger profile update."""
        self._turns_since_analysis += 1
        
        if self._turns_since_analysis >= self._analysis_interval:
            await self._update_profile_if_needed()
            self._turns_since_analysis = 0
    
    async def _update_profile_if_needed(self) -> None:
        """Update user profile from Layer 4 data."""
        try:
            self._profile_manager.analyze()
            logger.debug(f"User profile updated (confidence: {self._profile_manager.profile.confidence:.2f})")
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
    
    def get_profile(self):
        """Get current user profile."""
        return self._profile_manager.profile
    
    def get_profile_summary(self) -> str:
        """Get human-readable profile summary."""
        return self._profile_manager.get_profile_summary()
    
    def save_profile(self) -> None:
        """Save profile to disk."""
        self._profile_manager.save_profile()
    
    def load_profile(self) -> None:
        """Load profile from disk."""
        self._profile_manager.profile = self._profile_manager._load_or_create_profile()
