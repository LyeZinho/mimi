"""
Agent Orchestrator: coordena 7 brains autônomos.

- Gerencia lifecycle de cada brain
- Monitora health
- Fornece coordenação de estado
- Expõe API para controladores externos
"""

import asyncio
import logging
import time
from typing import Any

from agent.brains import (
    AvatarBrain,
    ExecutionBrain,
    InputBrain,
    OutputBrain,
    PlanningBrain,
    ReasoningBrain,
    SentimentBrain,
)
from agent.core.messaging import (
    Brain,
    EventType,
    get_event_bus,
    get_shared_state,
)
from agent.llm.provider import LLMProvider
from agent.output.pose_playback_controller import PosePlaybackController
from agent.output.tts_provider import TTSProvider

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orquestrador central de brains."""

    def __init__(
        self,
        user_id: str = "user_1",
        session_id: str | None = None,
        tts_provider: TTSProvider | None = None,
        llm_provider: LLMProvider | None = None,
        sentiment_engine=None,
    ):
        self.user_id = user_id
        self.session_id = session_id or f"session_{int(time.time())}"

        # Messaging
        self.event_bus = get_event_bus()
        self.shared_state = get_shared_state()

        # Store TTS and LLM providers for dependency injection
        self.tts_provider = tts_provider
        self.llm_provider = llm_provider
        self.sentiment_engine = sentiment_engine

        # === 3-BRAIN PIPELINE (Week 1-3A) ===
        # Initialization order: Input → Reasoning → Output
        # This ensures event chain flows correctly through the pipeline
        self.input_brain = InputBrain("input_brain", self.event_bus, self.shared_state)
        self.reasoning_brain = ReasoningBrain(
            llm_provider=self.llm_provider,
            brain_id="reasoning_brain",
            event_bus=self.event_bus,
            shared_state=self.shared_state,
        )

        # OutputBrain requires TTS provider via dependency injection
        if self.tts_provider is None:
            # Default: try to load PiperProvider if available
            try:
                from agent.output.config import PiperConfig
                from agent.output.piper_provider import PiperProvider

                config = PiperConfig(provider="piper", model="pt_BR")
                self.tts_provider = PiperProvider(config)
            except Exception as e:
                logger.warning(f"Could not initialize default TTS provider: {e}")

        # OutputBrain initialized with TTS provider
        # (may be None if initialization failed)
        self.output_brain = OutputBrain(
            brain_id="output_brain",
            event_bus=self.event_bus,
            shared_state=self.shared_state,
            tts_provider=self.tts_provider,
        )

        # ML Pose Playback Controller
        self.pose_controller = PosePlaybackController(self.event_bus, self.shared_state)

        # Remaining brains (exposed as attributes for health check and API access)
        self.planning_brain = PlanningBrain("planning_brain", self.event_bus, self.shared_state)
        self.execution_brain = ExecutionBrain("execution_brain", self.event_bus, self.shared_state)
        self.sentiment_brain = SentimentBrain(
            "sentiment_brain",
            self.event_bus,
            self.shared_state,
        )
        self.avatar_brain = AvatarBrain("avatar_brain", self.event_bus, self.shared_state)

        # 7 Brains (full system)
        self.brains: list[Brain] = [
            self.input_brain,
            self.reasoning_brain,
            self.planning_brain,
            self.execution_brain,
            self.sentiment_brain,
            self.avatar_brain,
            self.output_brain,
        ]

        self._running = False
        self._orchestrator_task: asyncio.Task | None = None
        self._health_check_interval = 5.0

    async def initialize(self) -> None:
        """Inicializa orchestrator e todos os brains."""
        logger.info(f"Initializing orchestrator (session: {self.session_id})")

        await self.shared_state.initialize(self.user_id, self.session_id)
        await self.event_bus.start()

        for brain in self.brains:
            await brain.initialize()
            logger.info(f"Initialized brain: {brain.brain_id}")

    async def start(self) -> None:
        """Inicia todos os brains."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("Starting orchestrator and all brains...")
        self._running = True

        for brain in self.brains:
            await brain.start()

        self._orchestrator_task = asyncio.create_task(self._orchestrator_loop())
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Para orchestrator e todos os brains."""
        logger.info("Stopping orchestrator...")
        self._running = False

        for brain in self.brains:
            await brain.shutdown()

        if self._orchestrator_task:
            await self._orchestrator_task

        await self.event_bus.stop()
        logger.info("Orchestrator stopped")

    async def _orchestrator_loop(self) -> None:
        """Loop principal do orchestrator."""
        while self._running:
            try:
                await self._health_check()
                await asyncio.sleep(self._health_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}", exc_info=True)

    async def _health_check(self) -> None:
        """Verifica health de todos os brains."""
        brain_health_map = await self.shared_state.get_all_brain_health()

        for brain_id, health in brain_health_map.items():
            is_healthy = health.is_healthy()
            status = "healthy" if is_healthy else "unhealthy"
            logger.debug(
                f"Brain {brain_id}: {status} "
                f"(events: {health.events_processed}, errors: {health.errors})"
            )

    # ===== PUBLIC API =====

    async def load_pose_sequence(self, pose_name: str, output_dir: str) -> bool:
        """Load a pose sequence for playback.

        Args:
            pose_name: Name of the pose sequence (e.g., 'sequence')
            output_dir: Directory containing pose files

        Returns:
            bool: True if sequence loaded successfully
        """
        return self.pose_controller.load_pose_sequence(output_dir, pose_name)

    async def play_pose(
        self, frame_id: int, fade_duration: float = 0.0
    ) -> dict[str, Any]:
        """Play a pose frame to the frontend avatar.

        Args:
            frame_id: Frame ID to play
            fade_duration: Transition duration in seconds

        Returns:
            Dict with success status and metadata
        """
        return self.pose_controller.play_pose(frame_id, fade_duration)

    async def start_pose_sequence(self, sequence_config: dict[str, Any]) -> bool:
        """Start playback of a pose sequence.

        Args:
            sequence_config: Configuration with start_frame, end_frame, loop, speed

        Returns:
            bool: True if sequence playback started successfully
        """
        return self.pose_controller.start_sequence_playback(sequence_config)

    async def process_text_input(self, text: str) -> None:
        """API: processa input de texto (simula Input Brain)."""
        # Simula que Input Brain publicou uma transcrição
        from agent.core.messaging import AgentEvent

        event = AgentEvent(
            type=EventType.TRANSCRIPTION_COMPLETE,
            source_brain="input_brain",
            payload={
                "transcript": text,
                "confidence": 1.0,
            },
        )

        await self.event_bus.publish(event)

    async def get_metrics(self) -> dict[str, Any]:
        """Retorna métricas do sistema."""
        brain_metrics = {}
        for brain in self.brains:
            brain_metrics[brain.brain_id] = brain.get_metrics()

        state_snapshot = await self.shared_state.get_full_snapshot()
        bus_metrics = self.event_bus.get_metrics()

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "running": self._running,
            "brains": brain_metrics,
            "state": state_snapshot,
            "event_bus": bus_metrics,
        }

    async def get_state_snapshot(self) -> dict[str, Any]:
        """Retorna snapshot do estado compartilhado."""
        return await self.shared_state.get_full_snapshot()

    async def get_event_history(
        self, event_type: str | None = None, limit: int = 50
    ) -> list[dict]:
        """Retorna histórico de eventos."""
        event_type_enum = None
        if event_type:
            try:
                event_type_enum = EventType[event_type.upper()]
            except KeyError:
                logger.warning(f"Unknown event type: {event_type}")

        events = self.event_bus.get_history(event_type_enum, limit)

        return [
            {
                "type": e.type.value,
                "source": e.source_brain,
                "timestamp": e.timestamp,
                "payload": e.payload,
            }
            for e in events
        ]
