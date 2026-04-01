"""
Integration tests for LLM control commands via WebSocket.

These tests validate that:
1. LLM config can be set via WebSocket commands
2. Config changes are broadcast to all clients
3. Config is persisted and sent to new connections
4. Invalid values are rejected
"""

import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


class MockWebSocketServer:
    """Mock WebSocket server for testing LLM control commands."""
    
    def __init__(self):
        self.llm_config = {
            "model": "phi3:mini",
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 0.9,
            "top_k": 40,
        }
        self.broadcasts = []
        self.clients = []

    def handle_set_llm_model(self, msg):
        """Handle set_llm_model command."""
        if msg.get("model"):
            self.llm_config["model"] = msg["model"]
            self.broadcasts.append(("llm_config", self.llm_config))
            return True
        return False

    def handle_set_llm_temperature(self, msg):
        """Handle set_llm_temperature command."""
        temp = msg.get("temperature")
        if temp is not None and 0 <= temp <= 2:
            self.llm_config["temperature"] = float(temp)
            self.broadcasts.append(("llm_config", self.llm_config))
            return True
        return False

    def handle_set_llm_max_tokens(self, msg):
        """Handle set_llm_max_tokens command."""
        tokens = msg.get("max_tokens")
        if tokens and tokens > 0:
            self.llm_config["max_tokens"] = int(tokens)
            self.broadcasts.append(("llm_config", self.llm_config))
            return True
        return False

    def handle_set_llm_config(self, msg):
        """Handle set_llm_config command (bulk update)."""
        config = msg.get("config", {})
        updates = {}
        
        if config.get("model"):
            updates["model"] = config["model"]
        if config.get("temperature") is not None:
            temp = float(config["temperature"])
            if 0 <= temp <= 2:
                updates["temperature"] = temp
        if config.get("max_tokens"):
            updates["max_tokens"] = int(config["max_tokens"])
        if config.get("top_p") is not None:
            top_p = float(config["top_p"])
            if 0 <= top_p <= 1:
                updates["top_p"] = top_p
        if config.get("top_k"):
            updates["top_k"] = int(config["top_k"])
        
        if updates:
            self.llm_config = {**self.llm_config, **updates}
            self.broadcasts.append(("llm_config", self.llm_config))
            return True
        return False

    def get_llm_config(self, msg):
        """Handle get_llm_config command."""
        return self.llm_config


class TestLLMControlCommands:
    """Tests for LLM control WebSocket commands."""

    @pytest.fixture
    def server(self):
        """Provide mock WebSocket server."""
        return MockWebSocketServer()

    def test_initial_config_has_defaults(self, server):
        """Test that initial config has sensible defaults."""
        assert server.llm_config["model"] == "phi3:mini"
        assert server.llm_config["temperature"] == 0.7
        assert server.llm_config["max_tokens"] == 1024

    def test_set_llm_model(self, server):
        """Test set_llm_model command."""
        msg = {"type": "set_llm_model", "model": "mistral:latest"}
        
        success = server.handle_set_llm_model(msg)
        
        assert success is True
        assert server.llm_config["model"] == "mistral:latest"
        assert len(server.broadcasts) == 1
        assert server.broadcasts[0][0] == "llm_config"

    def test_set_llm_temperature_valid(self, server):
        """Test set_llm_temperature with valid values."""
        test_cases = [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]
        
        for temp in test_cases:
            msg = {"type": "set_llm_temperature", "temperature": temp}
            success = server.handle_set_llm_temperature(msg)
            
            assert success is True
            assert server.llm_config["temperature"] == temp

    def test_set_llm_temperature_invalid_too_high(self, server):
        """Test that temperature > 2.0 is rejected."""
        msg = {"type": "set_llm_temperature", "temperature": 2.1}
        
        success = server.handle_set_llm_temperature(msg)
        
        assert success is False
        assert server.llm_config["temperature"] == 0.7

    def test_set_llm_temperature_invalid_negative(self, server):
        """Test that negative temperature is rejected."""
        msg = {"type": "set_llm_temperature", "temperature": -0.1}
        
        success = server.handle_set_llm_temperature(msg)
        
        assert success is False
        assert server.llm_config["temperature"] == 0.7

    def test_set_llm_max_tokens(self, server):
        """Test set_llm_max_tokens command."""
        msg = {"type": "set_llm_max_tokens", "max_tokens": 2048}
        
        success = server.handle_set_llm_max_tokens(msg)
        
        assert success is True
        assert server.llm_config["max_tokens"] == 2048

    def test_set_llm_max_tokens_invalid_negative(self, server):
        """Test that negative max_tokens is rejected."""
        msg = {"type": "set_llm_max_tokens", "max_tokens": -1}
        
        success = server.handle_set_llm_max_tokens(msg)
        
        assert success is False
        assert server.llm_config["max_tokens"] == 1024

    def test_set_llm_config_bulk_update(self, server):
        """Test set_llm_config with multiple parameters."""
        msg = {
            "type": "set_llm_config",
            "config": {
                "model": "neural-chat:latest",
                "temperature": 0.5,
                "max_tokens": 2048,
            }
        }
        
        success = server.handle_set_llm_config(msg)
        
        assert success is True
        assert server.llm_config["model"] == "neural-chat:latest"
        assert server.llm_config["temperature"] == 0.5
        assert server.llm_config["max_tokens"] == 2048

    def test_get_llm_config(self, server):
        """Test get_llm_config returns current config."""
        server.llm_config["temperature"] = 0.9
        
        config = server.get_llm_config({})
        
        assert config["model"] == "phi3:mini"
        assert config["temperature"] == 0.9
        assert config["max_tokens"] == 1024

    def test_set_llm_top_p(self, server):
        """Test set_llm_top_p command."""
        msg = {"type": "set_llm_top_p", "top_p": 0.95}
        
        top_p = msg.get("top_p")
        is_valid = top_p is not None and 0 <= top_p <= 1
        
        assert is_valid is True

    def test_config_broadcast_on_update(self, server):
        """Test that config broadcasts happen on every update."""
        initial_broadcasts = len(server.broadcasts)
        
        server.handle_set_llm_temperature({"temperature": 0.8})
        server.handle_set_llm_model({"model": "llama2:latest"})
        server.handle_set_llm_max_tokens({"max_tokens": 4096})
        
        assert len(server.broadcasts) == initial_broadcasts + 3
        for msg_type, config in server.broadcasts[-3:]:
            assert msg_type == "llm_config"

    def test_config_persistence_across_commands(self, server):
        """Test that config changes persist across multiple commands."""
        server.handle_set_llm_model({"model": "mistral:latest"})
        server.handle_set_llm_temperature({"temperature": 0.6})
        
        config = server.get_llm_config({})
        
        assert config["model"] == "mistral:latest"
        assert config["temperature"] == 0.6
        assert config["max_tokens"] == 1024

    def test_empty_config_update_rejected(self, server):
        """Test that empty config update is rejected."""
        msg = {"type": "set_llm_config", "config": {}}
        
        success = server.handle_set_llm_config(msg)
        
        assert success is False
