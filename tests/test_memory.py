"""Testes para o módulo de memória."""

import pytest

from agent.core.memory import Memory, MemoryEntry


def test_memory_add_and_recent():
    mem = Memory(short_term_limit=5)
    mem.add("Olá", role="user")
    mem.add("Oi!", role="assistant")

    recent = mem.recent()
    assert len(recent) == 2
    assert recent[0].content == "Olá"
    assert recent[1].role == "assistant"


def test_memory_limit():
    mem = Memory(short_term_limit=3)
    for i in range(5):
        mem.add(f"Mensagem {i}")

    recent = mem.recent()
    assert len(recent) == 3
    assert recent[0].content == "Mensagem 2"


def test_memory_entry_to_dict():
    entry = MemoryEntry(content="teste", role="user", importance=0.8)
    d = entry.to_dict()
    assert d["content"] == "teste"
    assert d["importance"] == 0.8
