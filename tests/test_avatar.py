"""Testes para integração com avatar."""

from __future__ import annotations

import pytest

from agent.avatar.interface import DummyAvatar, UnityAvatar


class TestAvatarIntegration:
    """Testa integração do avatar com o sistema."""

    @pytest.mark.asyncio
    async def test_dummy_avatar(self):
        """Testa avatar dummy."""
        avatar = DummyAvatar()
        
        await avatar.connect()
        await avatar.set_expression("happy")
        await avatar.speak_start()
        await avatar.speak_end()
        await avatar.disconnect()

    @pytest.mark.asyncio
    async def test_unity_avatar_creation(self):
        """Testa criação do UnityAvatar."""
        avatar = UnityAvatar(uri="ws://test:8080/")
        
        # Não conecta pois não há servidor
        assert not avatar.connected
        assert avatar.uri == "ws://test:8080/"

    def test_avatar_interface(self):
        """Testa contrato da interface."""
        avatar = DummyAvatar()
        
        # Verifica métodos existem
        assert hasattr(avatar, 'connect')
        assert hasattr(avatar, 'disconnect')
        assert hasattr(avatar, 'set_expression')
        assert hasattr(avatar, 'speak_start')
        assert hasattr(avatar, 'speak_end')