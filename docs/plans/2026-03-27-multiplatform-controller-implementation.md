# Multi-Platform Interactive Controller System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a modular controller system supporting Gamepad, Keyboard, and Mouse with intelligent action mapping and graceful degradation.

**Architecture:** A 3-phase approach: Core Adapters (infrastructure), Orchestration (logic), and Integration (system-wide connectivity). Uses an adapter-based pattern where abstract actions are resolved to concrete inputs based on device availability.

**Tech Stack:** Python 3.8+, pytest, pygame (gamepad), pynput (keyboard/mouse), dataclasses, asyncio.

---

### Phase 1: Core Adapters & Infrastructure

#### Task 1: Setup Controller Types & Base Adapter
**Files:**
- Create: `agent/controller/types.py`
- Create: `agent/controller/adapter_base.py`
- Test: `tests/controller/test_base.py`

**Step 1: Write the failing test**
```python
import pytest
from agent.controller.adapter_base import Adapter

def test_adapter_abstract_instantiation():
    with pytest.raises(TypeError):
        Adapter()
```
**Step 2: Run test to verify it fails**
Run: `pytest tests/controller/test_base.py`
Expected: FAIL (ModuleNotFound or ImportError)

**Step 3: Write minimal implementation**
`agent/controller/types.py`:
```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class ActionResult:
    action_id: str
    status: str
    device_used: str
    input_used: str
    actual_latency_ms: int
    fallback_used: bool = False
```
`agent/controller/adapter_base.py`:
```python
from abc import ABC, abstractmethod
from agent.controller.types import ActionResult

class Adapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    async def press(self, input_id: str, duration_ms: int) -> ActionResult: pass
```
**Step 4: Run test to verify it passes**
Run: `pytest tests/controller/test_base.py`
Expected: PASS

**Step 5: Commit**
```bash
git add agent/controller/ tests/controller/
git commit -m "feat(controller): add base adapter and types"
```

---

#### Task 2: Implement GamepadAdapter Mock/Skeleton
**Files:**
- Create: `agent/controller/gamepad_adapter.py`
- Test: `tests/controller/test_gamepad.py`

**Step 1: Write the failing test**
```python
import pytest
from agent.controller.gamepad_adapter import GamepadAdapter

@pytest.mark.asyncio
async def test_gamepad_press_a():
    adapter = GamepadAdapter()
    result = await adapter.press("A", 100)
    assert result.input_used == "A"
```
**Step 2: Run test to verify it fails**
Run: `pytest tests/controller/test_gamepad.py`
Expected: FAIL (ImportError)

**Step 3: Write minimal implementation**
`agent/controller/gamepad_adapter.py`:
```python
from agent.controller.adapter_base import Adapter
from agent.controller.types import ActionResult

class GamepadAdapter(Adapter):
    @property
    def name(self) -> str: return "gamepad"
    
    async def press(self, input_id: str, duration_ms: int) -> ActionResult:
        return ActionResult(action_id="test", status="success", device_used="gamepad", input_used=input_id, actual_latency_ms=10)
```
**Step 4: Run test to verify it passes**
Run: `pytest tests/controller/test_gamepad.py`
Expected: PASS

**Step 5: Commit**
```bash
git add agent/controller/gamepad_adapter.py tests/controller/test_gamepad.py
git commit -m "feat(controller): add gamepad adapter skeleton"
```

---

#### Task 3: Integrate Pygame for Gamepad Input
**Files:**
- Modify: `agent/controller/gamepad_adapter.py`
- Test: `tests/controller/test_gamepad_hw.py`

**Step 1: Write failing test (requires hardware or mock)**
```python
from unittest.mock import MagicMock, patch
import pytest
from agent.controller.gamepad_adapter import GamepadAdapter

@pytest.mark.asyncio
async def test_gamepad_pygame_init():
    with patch('pygame.joystick.init') as mock_init:
        adapter = GamepadAdapter()
        adapter.initialize()
        mock_init.assert_called_once()
```
**Step 2: Run test to verify it fails**
Run: `pytest tests/controller/test_gamepad_hw.py`
Expected: FAIL (AttributeError: 'GamepadAdapter' object has no attribute 'initialize')

**Step 3: Write minimal implementation**
`agent/controller/gamepad_adapter.py`:
```python
import pygame
class GamepadAdapter(Adapter):
    def initialize(self):
        pygame.joystick.init()
    # ... rest of implementation
```
**Step 4: Run test to verify it passes**
Run: `pytest tests/controller/test_gamepad_hw.py`
Expected: PASS

**Step 5: Commit**
```bash
git commit -am "feat(controller): integrate pygame for gamepad initialization"
```

---

#### Task 4: Implement KeyboardAdapter with pynput
**Files:**
- Create: `agent/controller/keyboard_adapter.py`
- Test: `tests/controller/test_keyboard.py`

**Step 1: Write failing test**
```python
@pytest.mark.asyncio
async def test_keyboard_press_space():
    adapter = KeyboardAdapter()
    result = await adapter.press("SPACE", 100)
    assert result.device_used == "keyboard"
```
**Step 2: Run test to verify it fails**
Expected: FAIL

**Step 3: Write minimal implementation using pynput.keyboard.Controller**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 5: Implement MouseAdapter with pynput
**Files:**
- Create: `agent/controller/mouse_adapter.py`
- Test: `tests/controller/test_mouse.py`

**Step 1: Write failing test for mouse click**
**Step 2: Run test to verify it fails**
**Step 3: Write implementation using pynput.mouse.Controller**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 6: Add Capability Registration to Adapters
**Files:**
- Modify: `agent/controller/adapter_base.py`
- Modify: `agent/controller/gamepad_adapter.py`
- Test: `tests/controller/test_capabilities.py`

**Step 1: Write test for get_capabilities()**
**Step 2: Run test to verify it fails**
**Step 3: Implement get_capabilities returning List[str] of supported inputs**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 7: Implement Adapter State Monitoring
**Files:**
- Modify: `agent/controller/types.py`
- Modify: `agent/controller/adapter_base.py`
- Test: `tests/controller/test_state.py`

**Step 1: Write test for is_available property**
**Step 2: Run test to verify it fails**
**Step 3: Implement availability check (e.g., check if hardware connected)**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

### Phase 2: Orchestration Components

#### Task 8: Implement GameManifest Parser
**Files:**
- Modify: `agent/controller/types.py`
- Create: `agent/controller/manifest_parser.py`
- Test: `tests/controller/test_manifest.py`

**Step 1: Write test to parse YAML manifest into GameManifest dataclass**
**Step 2: Run test to verify it fails**
**Step 3: Implement parser using PyYAML**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 9: Implement CapabilityNegotiator
**Files:**
- Create: `agent/controller/negotiator.py`
- Test: `tests/controller/test_negotiator.py`

**Step 1: Write test that maps GameManifest actions to available Adapters**
**Step 2: Run test to verify it fails**
**Step 3: Implement negotiator logic (intersect manifest requirements with adapter capabilities)**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 10: Implement ActionResolver (Primary Path)
**Files:**
- Create: `agent/controller/resolver.py`
- Test: `tests/controller/test_resolver.py`

**Step 1: Write test for resolving "jump" to a ConcreteAction**
**Step 2: Run test to verify it fails**
**Step 3: Implement basic resolver using CapabilityMap**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 11: Implement Fallback Logic in ActionResolver
**Files:**
- Modify: `agent/controller/resolver.py`
- Test: `tests/controller/test_resolver_fallbacks.py`

**Step 1: Write test for fallback chain when primary device is unavailable**
**Step 2: Run test to verify it fails**
**Step 3: Implement fallback list generation in ExecutionPlan**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 12: Implement ControllerManager Initialization
**Files:**
- Create: `agent/controller/manager.py`
- Test: `tests/controller/test_manager_init.py`

**Step 1: Write test for manager.initialize(manifest)**
**Step 2: Run test to verify it fails**
**Step 3: Implement manager that holds adapters and negotiator**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 13: Implement ControllerManager Execution Loop
**Files:**
- Modify: `agent/controller/manager.py`
- Test: `tests/controller/test_manager_execute.py`

**Step 1: Write test for manager.execute_action(request)**
**Step 2: Run test to verify it fails**
**Step 3: Implement execution logic: Resolver -> Adapter.press()**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 14: Implement Graceful Degradation in Manager
**Files:**
- Modify: `agent/controller/manager.py`
- Test: `tests/controller/test_manager_degradation.py`

**Step 1: Write test that fails primary and succeeds on fallback**
**Step 2: Run test to verify it fails**
**Step 3: Implement try-except loop over execution plan fallbacks**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 15: Implement Latency Budget Enforcement
**Files:**
- Modify: `agent/controller/manager.py`
- Test: `tests/controller/test_latency.py`

**Step 1: Write test that warns when latency exceeds budget**
**Step 2: Run test to verify it fails**
**Step 3: Implement timing logic around adapter calls**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

### Phase 3: Integration

#### Task 16: Integrate with Event Bus
**Files:**
- Modify: `agent/controller/manager.py`
- Test: `tests/controller/test_events.py`

**Step 1: Write test for 'controller.action_executed' event emission**
**Step 2: Run test to verify it fails**
**Step 3: Use agent.core.messaging.event_bus to emit results**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 17: Extend Action Router for Controller Actions
**Files:**
- Modify: `agent/output/actions.py`
- Test: `tests/integration/test_action_routing.py`

**Step 1: Write test for 'controller_action' type handling**
**Step 2: Run test to verify it fails**
**Step 3: Implement @action_handler("controller_action")**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 18: Context Injection for LLM
**Files:**
- Modify: `agent/brains/execution_brain.py`
- Test: `tests/integration/test_llm_context.py`

**Step 1: Write test ensuring capability map is in prompt context**
**Step 2: Run test to verify it fails**
**Step 3: Update ExecutionBrain to fetch capabilities from ControllerManager**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 19: Full Pipeline Integration Test
**Files:**
- Create: `tests/integration/test_controller_pipeline.py`

**Step 1: Write test: Manifest -> Manager -> Action Request -> Success Result**
**Step 2: Run test to verify it fails**
**Step 3: Fix integration issues (mocking hardware if needed)**
**Step 4: Run test to verify it passes**
**Step 5: Commit**

---

#### Task 20: Documentation & Final Cleanup
**Files:**
- Create: `docs/CONTROLLER_SYSTEM.md`
- Modify: `README.md`

**Step 1: Write documentation for new system**
**Step 2: Verify all lsp_diagnostics are clean**
**Step 3: Run full test suite: `pytest tests/controller tests/integration`**
**Step 4: Final commit and cleanup**

---

Plan complete and saved to `docs/plans/2026-03-27-multiplatform-controller-implementation.md`. 
Approach: **Subagent-Driven (this session)** recommended for rapid TDD cycle.
