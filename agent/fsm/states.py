from enum import Enum

class AgentStateEnum(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    ERROR = "error"

VALID_TRANSITIONS: dict[AgentStateEnum, set[AgentStateEnum]] = {
    AgentStateEnum.IDLE:       {AgentStateEnum.LISTENING},
    AgentStateEnum.LISTENING:  {AgentStateEnum.PROCESSING, AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.PROCESSING: {AgentStateEnum.SPEAKING, AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.SPEAKING:   {AgentStateEnum.IDLE, AgentStateEnum.ERROR},
    AgentStateEnum.ERROR:      {AgentStateEnum.IDLE},
}
