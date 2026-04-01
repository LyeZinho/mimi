"""Interface abstrata para avatar 3D."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import websockets
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AvatarCommand(BaseModel):
    """Comando para enviar ao avatar."""

    type: str = "avatar_control"
    emotion: str | None = None
    gesture: str | None = None
    speak: bool = False
    speech_text: str | None = None
    audio_base64: str | None = None
    model_path: str | None = None
    model_base64: str | None = None
    model_name: str | None = None


class AvatarInterface(ABC):
    """Contrato para integração com avatares 3D (Unity, VTube Studio, VRM)."""

    @abstractmethod
    async def set_expression(self, name: str) -> None:
        """Define expressão facial do avatar."""
        ...

    @abstractmethod
    async def speak_start(self) -> None:
        """Notifica início da fala (lip-sync, animação)."""
        ...

    @abstractmethod
    async def speak_end(self) -> None:
        """Notifica fim da fala."""
        ...

    @abstractmethod
    async def load_model_from_path(self, path: str) -> None:
        """Carrega modelo VRM de um caminho absoluto."""
        ...

    @abstractmethod
    async def load_model_from_base64(self, base64_data: str, name: str) -> None:
        """Carrega modelo VRM de dados base64."""
        ...

    @abstractmethod
    async def connect(self) -> None:
        """Conecta ao avatar."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Desconecta do avatar."""
        ...


class DummyAvatar(AvatarInterface):
    """Avatar placeholder para testes."""

    async def connect(self) -> None:
        logger.info("DummyAvatar conectado")

    async def disconnect(self) -> None:
        logger.info("DummyAvatar desconectado")

    async def set_expression(self, name: str) -> None:
        pass

    async def speak_start(self) -> None:
        pass

    async def speak_end(self) -> None:
        pass

    async def load_model_from_path(self, path: str) -> None:
        pass

    async def load_model_from_base64(self, base64_data: str, name: str) -> None:
        pass


class WebAvatar(AvatarInterface):
    """Cliente WebSocket para conectar ao backend do avatar."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.ws = None
        self.connected = False
        self.agent = None
        self.listen_task = None
        self.message_callback = None

    def set_agent(self, agent: Any) -> None:
        self.agent = agent

    def set_message_callback(self, callback: Any) -> None:
        self.message_callback = callback

    async def connect(self) -> None:
        """Conecta ao servidor WebSocket (Backend)."""
        uri = f"ws://{self.host}:{self.port}"
        logger.info(f"Conectando ao backend em {uri}...")
        try:
            self.ws = await websockets.connect(uri)
            self.connected = True
            logger.info("Conectado ao backend WebAvatar")
            
            await self.send_identify()
            
            self.listen_task = asyncio.create_task(self._listen_loop())
            await asyncio.sleep(0.01)
            logger.info(f"[CONNECT] Listen task started: {self.listen_task.get_name()}")

        except Exception as e:
            logger.error(f"Falha ao conectar ao backend: {e}")
            self.connected = False

    async def send_identify(self) -> None:
        """Sends identify message to establish agent role."""
        try:
            identify_msg = {
                "type": "identify",
                "role": "agent"
            }
            await self.ws.send(json.dumps(identify_msg))
            logger.info("Agent identified to server")
        except Exception as e:
            logger.error(f"Failed to send identify: {e}")
            raise

    async def disconnect(self) -> None:
        if self.ws:
            await self.ws.close()
            self.ws = None
        if self.listen_task:
            self.listen_task.cancel()
        self.connected = False
        logger.info("Desconectado do backend")

    async def _listen_loop(self):
        """Escuta mensagens do servidor."""
        logger.info("[LISTEN] Starting listen loop...")
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    logger.info(f"[LISTEN] Message received: type={msg_type}")
                    
                    if self.message_callback:
                        logger.info(f"[LISTEN] Calling message_callback for type={msg_type}")
                        await self.message_callback(data)
                    else:
                        logger.warning(f"[LISTEN] No message_callback set, ignoring: {msg_type}")

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    if "readonly database" in str(e):
                        logger.warning(f"Database error (ignoring): {e}")
                    else:
                        logger.error(
                            f"[LISTEN] Erro processando mensagem: {e}", exc_info=True
                        )
                    continue
        except Exception as e:
            logger.error(f"[LISTEN] Listen loop error: {e}", exc_info=True)

    async def send_command(self, data: dict) -> None:
        if self.connected and self.ws:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                logger.error(f"Erro ao enviar comando: {e}")

    async def set_expression(self, name: str) -> None:
        await self.send_command({"type": "set_expression", "expression": name})

    async def speak_start(self) -> None:
        await self.send_command({"type": "set_speaking", "speaking": True})

    async def speak_end(self) -> None:
        await self.send_command({"type": "set_speaking", "speaking": False})

    async def load_model_from_path(self, path: str) -> None:
        filename = Path(path).name
        await self.send_command({"type": "set_model", "model": filename})

    async def load_model_from_base64(self, base64_data: str, name: str) -> None:
        pass
