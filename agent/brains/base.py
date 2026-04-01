import abc
import logging
from typing import Any

log = logging.getLogger(__name__)


class BrainBase(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute brain logic. Receives context dict, returns updated context."""

    async def setup(self) -> None:
        """Optional async initialization."""

    async def teardown(self) -> None:
        """Optional async cleanup."""


class BrainRegistry:
    def __init__(self) -> None:
        self._brains: dict[str, BrainBase] = {}

    def register(self, brain: BrainBase) -> None:
        self._brains[brain.name] = brain
        log.debug("Registered brain: %s", brain.name)

    def get(self, name: str) -> BrainBase:
        if name not in self._brains:
            raise KeyError(f"Brain '{name}' not registered. Available: {list(self._brains)}")
        return self._brains[name]

    async def run_pipeline(
        self, pipeline: list[str], context: dict[str, Any]
    ) -> dict[str, Any]:
        for name in pipeline:
            brain = self.get(name)
            log.debug("Running brain: %s", name)
            try:
                context = await brain.run(context)
            except Exception:
                log.exception("Brain '%s' failed", name)
                raise
        return context

    async def setup_all(self) -> None:
        for brain in self._brains.values():
            await brain.setup()

    async def teardown_all(self) -> None:
        for brain in self._brains.values():
            await brain.teardown()
