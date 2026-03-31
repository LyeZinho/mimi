import pytest
from datetime import datetime
from agent.schemas import (
    TranscriptEvent, SentimentResult, AgentContext,
    ResponsePlan, AgentStateSnapshot, MemoryEntry, ToolCall
)


def test_transcript_event_defaults():
    t = TranscriptEvent(text="hello", confidence=0.95)
    assert t.text == "hello"
    assert isinstance(t.timestamp, datetime)


def test_sentiment_result_valid_emotions():
    s = SentimentResult(emotion="happy", intensity=0.8)
    assert s.emotion == "happy"


def test_sentiment_result_invalid_emotion():
    with pytest.raises(Exception):
        SentimentResult(emotion="bored", intensity=0.5)


def test_response_plan_default_no_tools():
    r = ResponsePlan(text="hi", action="speak")
    assert r.tool_calls == []


def test_agent_state_snapshot():
    snap = AgentStateSnapshot(
        fsm_state="idle", active_brain="none",
        last_emotion="neutral", last_transcript="",
        latency_ms=0
    )
    assert snap.fsm_state == "idle"
