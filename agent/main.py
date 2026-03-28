"""Entry point do agente Mimi — Orchestrator mode."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from agent.avatar.interface import DummyAvatar, WebAvatar
from agent.bridge import OrchestratorBridge
from agent.config import (
    AVATAR_TYPE,
    LLM_MODEL,
    WEBSOCKET_HOST,
    WEBSOCKET_PORT,
)
from agent.core.health_check import BrainHealthCheck
from agent.llm.config import OllamaConfig
from agent.llm.ollama_provider import OllamaProvider
from agent.orchestrator import AgentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://api.ollama.ai")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")


def create_avatar() -> DummyAvatar | WebAvatar:
    """Create avatar instance based on config."""
    if AVATAR_TYPE == "web":
        return WebAvatar(host=WEBSOCKET_HOST, port=WEBSOCKET_PORT)
    else:
        return DummyAvatar()


def create_tts_provider():
    """Create TTS provider with graceful fallback."""
    try:
        from agent.output.config import PiperConfig
        from agent.output.piper_provider import PiperProvider

        config = PiperConfig(provider="piper", model="pt_PT")
        provider = PiperProvider(config)
        logger.info("PiperTTS provider initialized")
        return provider
    except Exception as e:
        logger.warning(f"PiperTTS not available ({e}), OutputBrain will have no TTS")
        return None


def create_llm_provider():
    """Create Ollama LLM provider."""
    try:
        host = OLLAMA_HOST
        config = OllamaConfig(
            provider="ollama",
            model=LLM_MODEL,
            host=host,
            temperature=0.7,
        )
        provider = OllamaProvider(config)
        logger.info(f"OllamaProvider initialized (model={LLM_MODEL}, host={host})")
        return provider
    except Exception as e:
        logger.warning(
            f"OllamaProvider not available ({e}), ReasoningBrain will use fallback"
        )
        return None


async def main() -> None:
    """Initialize and run the Mimi agent with full Orchestrator."""
    print("=" * 50)
    print("  Mimi – Agente de IA (Orchestrator Mode)")
    print("=" * 50)
    logger.info("Starting agent in Orchestrator mode...")

    # Components
    avatar = create_avatar()
    tts_provider = create_tts_provider()
    llm_provider = create_llm_provider()

    # Create Orchestrator with all dependencies
    orchestrator = AgentOrchestrator(
        tts_provider=tts_provider,
        llm_provider=llm_provider,
    )

    # Create Bridge (WS ↔ EventBus)
    bridge = OrchestratorBridge(
        avatar=avatar,
        event_bus=orchestrator.event_bus,
    )

    # Set Bridge as message handler on WebAvatar
    if isinstance(avatar, WebAvatar):

        async def on_ws_message(data: dict):
            """Bridge callback for incoming WebSocket messages."""
            msg_type = data.get("type")
            if msg_type in ("agent_input", "chat"):
                text = data.get("text") or data.get("message", "")
                if text:
                    await bridge.handle_text_input(text, source="web")
            elif msg_type == "audio_chunk":
                audio_data = data.get("data")
                sample_rate = data.get("sample_rate", 16000)
                if audio_data:
                    await bridge.handle_audio_chunk(audio_data, sample_rate)
            elif msg_type == "state":
                pass
            else:
                logger.debug(f"Unhandled WS message type in bridge: {msg_type}")

        avatar.set_message_callback(on_ws_message)

    try:
        # Connect WebSocket
        await avatar.connect()
        logger.info("Avatar connected")

        # Load default model
        if isinstance(avatar, WebAvatar):
            await avatar.load_model_from_path("vroid_model/Mimi.vrm")
            logger.info("Default model Mimi.vrm loaded")

        # Initialize and start Orchestrator (all 7 brains)
        await orchestrator.initialize()
        logger.info("Orchestrator initialized with all brains")

        # Run health checks on all brains (before starting background loops)
        logger.info("Running brain health checks...")
        health_check = BrainHealthCheck(orchestrator.event_bus)

        brains = {
            "InputBrain": orchestrator.input_brain,
            "ReasoningBrain": orchestrator.reasoning_brain,
            "PlanningBrain": orchestrator.planning_brain,
            "ExecutionBrain": orchestrator.execution_brain,
            "SentimentBrain": orchestrator.sentiment_brain,
            "AvatarBrain": orchestrator.avatar_brain,
            "OutputBrain": orchestrator.output_brain,
        }

        try:
            all_operational = await asyncio.wait_for(
                health_check.run(brains, timeout=5), timeout=30
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ Health check timed out - starting anyway")
            all_operational = False

        if all_operational:
            logger.info("✅ All brains operational - Agent ready")
        else:
            # Collect detailed information about failed brains
            failed_brains = []
            timeout_brains = []
            for brain_name, result in health_check.results.items():
                status = result.get("status", "unknown")
                details = result.get("details", "unknown reason")
                if status == "failed":
                    failed_brains.append(f"✗ {brain_name}: {details}")
                elif status == "timeout":
                    timeout_brains.append(f"⚠ {brain_name}: {details}")

            # Log detailed warnings
            if failed_brains or timeout_brains:
                logger.warning(
                    "⚠️ Brain health check issues detected:"
                )
                for brain_issue in failed_brains:
                    logger.error(f"  {brain_issue}")
                for brain_issue in timeout_brains:
                    logger.warning(f"  {brain_issue}")
                logger.warning(
                    "Starting agent anyway - some functionality may be degraded"
                )

        # Now start orchestrator (begins background processing loops)
        await orchestrator.start()
        logger.info("Orchestrator started with all brains")

        # Start Bridge
        await bridge.start()
        logger.info("Bridge connected: WebSocket ↔ EventBus")

        logger.info("System ready. Waiting for input...")

        # Keep alive
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Interrupt received")
    except Exception as e:
        logger.error(f"Daemon error: {e}", exc_info=True)
    finally:
        await bridge.stop()
        await orchestrator.stop()
        await avatar.disconnect()
        if llm_provider and hasattr(llm_provider, "close"):
            await llm_provider.close()
        logger.info("Daemon stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
