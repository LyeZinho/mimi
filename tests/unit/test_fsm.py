import pytest
from agent.fsm.states import AgentStateEnum, VALID_TRANSITIONS
from agent.fsm.agent_fsm import AgentFSM

def test_valid_transitions_defined():
    assert AgentStateEnum.IDLE in VALID_TRANSITIONS
    assert AgentStateEnum.LISTENING in VALID_TRANSITIONS[AgentStateEnum.IDLE]

@pytest.mark.asyncio
async def test_fsm_starts_idle():
    fsm = AgentFSM()
    assert fsm.state == AgentStateEnum.IDLE

@pytest.mark.asyncio
async def test_fsm_valid_transition():
    fsm = AgentFSM()
    await fsm.transition(AgentStateEnum.LISTENING)
    assert fsm.state == AgentStateEnum.LISTENING

@pytest.mark.asyncio
async def test_fsm_invalid_transition_raises():
    fsm = AgentFSM()
    with pytest.raises(ValueError, match="Invalid transition"):
        await fsm.transition(AgentStateEnum.SPEAKING)

@pytest.mark.asyncio
async def test_fsm_error_recovery():
    fsm = AgentFSM()
    await fsm.transition(AgentStateEnum.LISTENING)
    await fsm.transition(AgentStateEnum.ERROR)
    await fsm.transition(AgentStateEnum.IDLE)
    assert fsm.state == AgentStateEnum.IDLE
