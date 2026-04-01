"""Testes para o módulo de estado."""

from agent.core.state import AgentState


def test_state_defaults():
    state = AgentState()
    assert state.mood == "neutral"
    assert state.speaking is False


def test_state_set_known_attr():
    state = AgentState()
    state.set("mood", "happy")
    assert state.mood == "happy"


def test_state_set_custom():
    state = AgentState()
    state.set("energia", 100)
    assert state.get("energia") == 100
    assert state.custom["energia"] == 100


def test_state_summary():
    state = AgentState(mood="curious", focus="tarefa")
    summary = state.summary()
    assert summary["mood"] == "curious"
    assert summary["focus"] == "tarefa"
