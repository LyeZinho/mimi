import asyncio
import logging
from collections.abc import Callable, Awaitable
from agent.fsm.states import AgentStateEnum, VALID_TRANSITIONS
from agent.schemas import AgentStateSnapshot

log = logging.getLogger(__name__)

StateCallback = Callable[[AgentStateEnum, AgentStateEnum], Awaitable[None]]


class AgentFSM:
    def __init__(self) -> None:
        self._state = AgentStateEnum.IDLE
        self._lock = asyncio.Lock()
        self._callbacks: list[StateCallback] = []

    @property
    def state(self) -> AgentStateEnum:
        return self._state

    def on_transition(self, cb: StateCallback) -> None:
        self._callbacks.append(cb)

    async def transition(self, new_state: AgentStateEnum) -> None:
        async with self._lock:
            allowed = VALID_TRANSITIONS.get(self._state, set())
            if new_state not in allowed:
                raise ValueError(
                    f"Invalid transition: {self._state} → {new_state}. Allowed: {allowed}"
                )
            old = self._state
            self._state = new_state
            log.debug("FSM: %s → %s", old, new_state)

        for cb in self._callbacks:
            try:
                await cb(old, new_state)
            except Exception:
                log.exception("FSM callback error")
