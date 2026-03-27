"""
OrchestratorBridge: translates between WebAvatar (WebSocket) and EventBus.

Inbound: WS messages → EventBus events
Outbound: EventBus events → WS messages via WebAvatar
"""

import logging
from typing import Any

from agent.core.messaging import AgentEvent, EventBus, EventType

logger = logging.getLogger(__name__)


class OrchestratorBridge:
    """Connects WebAvatar (WS client) to the EventBus (brain communication)."""

    def __init__(self, avatar: Any, event_bus: EventBus):
        self.avatar = avatar
        self.event_bus = event_bus
        self._running = False

    async def start(self) -> None:
        """Subscribe to EventBus events for outbound translation."""
        self._running = True

        # Outbound: EventBus → WebAvatar
        self.event_bus.subscribe(EventType.RESPONSE_READY)(self._on_response_ready)
        self.event_bus.subscribe(EventType.ANIMATION_QUEUED)(self._on_animation_queued)
        self.event_bus.subscribe(EventType.GESTURE_QUEUED)(self._on_gesture_queued)
        self.event_bus.subscribe(EventType.TTS_STARTED)(self._on_tts_started)
        self.event_bus.subscribe(EventType.AUDIO_COMPLETE)(self._on_audio_complete)
        self.event_bus.subscribe(EventType.EMOTION_DETECTED)(self._on_emotion_detected)

        logger.info("OrchestratorBridge started — subscribed to EventBus")

    async def stop(self) -> None:
        """Stop the bridge."""
        self._running = False
        logger.info("OrchestratorBridge stopped")

    # ===== INBOUND: WS → EventBus =====

    async def handle_text_input(self, text: str, source: str = "web") -> None:
        """Called when text arrives via WebSocket. Publishes TRANSCRIPTION_COMPLETE."""
        event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="bridge",
            payload={
                "transcript": text,
                "confidence": 1.0,
                "source": source,
            },
        )
        await self.event_bus.publish(event)
        logger.info(f"Bridge published TRANSCRIPTION_COMPLETE: {text[:50]}...")

    # ===== OUTBOUND: EventBus → WS =====

    async def _on_response_ready(self, event: AgentEvent) -> None:
        """Send agent response back through WebSocket."""
        response = event.payload.get("response", "")
        if response:
            await self.avatar.send_command(
                {
                    "type": "agent_response",
                    "text": response,
                }
            )
            logger.info(f"Bridge sent agent_response: {response[:50]}...")

    async def _on_animation_queued(self, event: AgentEvent) -> None:
        """Send avatar emotion/animation control."""
        sentiment = event.payload.get("sentiment", "neutral")
        animation = event.payload.get("animation", "neutral")
        await self.avatar.send_command(
            {
                "type": "avatar_control",
                "emotion": sentiment,
                "gesture": animation,
            }
        )

    async def _on_gesture_queued(self, event: AgentEvent) -> None:
        """Send avatar gesture control."""
        gesture = event.payload.get("gesture", "idle")
        intensity = event.payload.get("intensity", 0.0)
        await self.avatar.send_command(
            {
                "type": "avatar_control",
                "gesture": gesture,
                "intensity": intensity,
            }
        )

    async def _on_tts_started(self, event: AgentEvent) -> None:
        """Notify avatar that speech has started."""
        await self.avatar.speak_start()

    async def _on_audio_complete(self, event: AgentEvent) -> None:
        """Notify avatar that speech has ended."""
        await self.avatar.speak_end()

    async def _on_emotion_detected(self, event: AgentEvent) -> None:
        """Set avatar expression based on detected emotion."""
        sentiment = event.payload.get("sentiment", "neutral")
        await self.avatar.set_expression(sentiment)
