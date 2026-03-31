from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TranscriptEvent(BaseModel):
    text: str
    confidence: float = 1.0
    timestamp: datetime = Field(default_factory=_utc_now)


class SentimentResult(BaseModel):
    emotion: Literal["neutral", "happy", "sad", "angry", "surprised", "curious"]
    intensity: float = Field(ge=0.0, le=1.0)


class MemoryEntry(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=_utc_now)


class ToolCall(BaseModel):
    name: str
    args: dict = Field(default_factory=dict)


class AgentContext(BaseModel):
    transcript: TranscriptEvent
    sentiment: SentimentResult | None = None
    memory: list[MemoryEntry] = Field(default_factory=list)
    session_id: str


class ResponsePlan(BaseModel):
    text: str
    action: Literal["speak", "speak+tool", "silence"] = "speak"
    tool_calls: list[ToolCall] = Field(default_factory=list)


class AgentStateSnapshot(BaseModel):
    fsm_state: str
    active_brain: str
    last_emotion: str
    last_transcript: str
    latency_ms: int
