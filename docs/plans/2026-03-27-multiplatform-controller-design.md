# Multi-Platform Interactive Controller System Design

**Date:** 2026-03-27  
**Status:** Design Complete (Ready for Implementation Planning)  
**Approach:** Hybrid Intelligence (Abordagem 3)  
**Integration:** Extension of Execution Brain  
**Last Updated:** 2026-03-27

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Component Details](#component-details)
4. [Adapter Interface & Contract](#adapter-interface--contract)
5. [Data Structures & Message Types](#data-structures--message-types)
6. [Error Handling & Fallback Strategy](#error-handling--fallback-strategy)
7. [Game Manifest Format & Runtime API](#game-manifest-format--runtime-api)
8. [Integration with Execution Brain](#integration-with-execution-brain)
9. [Implementation Phases](#implementation-phases)

---

## Overview

### Problem Statement

Mimi needs a **dynamic, multi-platform interactive controller system** to interact with games and applications beyond just web navigation. The system must:

- Support multiple input devices (gamepad, keyboard, mouse) as foundation
- Be generic enough for future expansion to other devices (VR controllers, touch, etc.)
- Intelligently map abstract actions (e.g., "jump") to concrete device inputs
- Gracefully degrade when devices are unavailable
- Integrate seamlessly with the Execution Brain's action routing
- Never throw errors; always provide rich feedback and auto-configuration

### Design Principles

1. **Adapter-Centric:** Each input device is an adapter with a well-defined interface
2. **Hybrid Intelligence:** Game requirements + adapter capabilities → LLM decides execution
3. **Graceful Degradation:** Try primary action → fallback to alternative → auto-calibrate
4. **Rich Feedback:** Every action produces detailed result info (success/failure/why/fallback-used)
5. **Config-Driven Discovery:** Adapters registered in config; auto-discovery for new devices
6. **Per-Adapter State:** Each adapter maintains independent state; event broadcast for coordination
7. **Adaptive Latency:** Game specifies latency budget; system throttles accordingly
8. **Manifest-First Integration:** Games provide capabilities; runtime API allows dynamic adjustments

---

## Architecture

### High-Level System Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Game/Application                      │
│  (Manifest: required actions, device preferences)       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│            Execution Brain (Extended)                    │
│  - Action Router (new: controller_action handler)       │
│  - Event Bus (broadcasts adapter state changes)         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────┐
│           Controller Manager (NEW)                       │
│  Orchestrates: Negotiator → Resolver → Adapters        │
│  - Handles latency budgets                              │
│  - Broadcasts state events                              │
│  - Manages fallback chains                              │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┬─────────────────┐
        ↓                         ↓                 ↓
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Capability       │    │ Action Resolver  │    │ Event Broadcast  │
│ Negotiator       │    │                  │    │                  │
│                  │    │ Concrete Mapping │    │ (State Updates)  │
│ Game Manifest +  │    │ Primary → Fallback   │                  │
│ Adapter Registry │    │ Action Translation   │                  │
│ → Capability Map │    │                  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                       │                        │
        └───────────────────────┼────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ↓               ↓               ↓
         ┌────────────┐  ┌────────────┐  ┌────────────┐
         │ Gamepad    │  │ Keyboard   │  │ Mouse      │
         │ Adapter    │  │ Adapter    │  │ Adapter    │
         └────────────┘  └────────────┘  └────────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                                ↓
                        ┌─────────────────┐
                        │  Operating      │
                        │  System         │
                        │  (Input Events) │
                        └─────────────────┘
```

### Data Flow Example: "Jump" Action

```
1. Game sends action request:
   {
     "action": "jump",
     "game_id": "platformer_v1",
     "latency_budget_ms": 50
   }

2. Controller Manager calls Capability Negotiator:
   - Queries game manifest for "jump"
   - Checks available adapters
   - Returns: ["gamepad.A", "keyboard.W", "keyboard.SPACE"]

3. LLM (via Execution Brain) receives capability map:
   - "Jump is possible via: gamepad.A OR keyboard.W OR keyboard.SPACE"
   - Decides: "use gamepad.A (preferred for games)"

4. Action Resolver translates to concrete action:
   - Primary: {adapter: "gamepad", input: "A", duration_ms: 100, intensity: 1.0}
   - Fallback: {adapter: "keyboard", input: "W", duration_ms: 100, intensity: 1.0}

5. Controller Manager executes:
   - Calls GamepadAdapter.press("A", duration_ms=100, intensity=1.0)
   - If fails → tries KeyboardAdapter.press("W", ...)
   - If fails → broadcasts calibration event + returns rich error info

6. Result sent back to Execution Brain:
   {
     "action": "jump",
     "status": "success",
     "device_used": "gamepad",
     "button_pressed": "A",
     "latency_ms": 32,
     "fallback_used": false
   }
```

---

## Component Details

### 1. CapabilityNegotiator

**Purpose:** Reconcile game requirements with available adapter capabilities.

**Inputs:**
- `game_manifest: GameManifest` - Game's capability requirements
- `adapter_registry: Dict[str, Adapter]` - Available adapters

**Outputs:**
- `capability_map: CapabilityMap` - Mapping of actions to possible device inputs

**Logic:**
```
For each action in game_manifest.required_actions:
  - Check each adapter for compatibility
  - Build list of possible inputs (primary + fallbacks)
  - Store as: action_name → [input_option_1, input_option_2, ...]

Example:
  "jump" → [
    {adapter: "gamepad", input: "A", intensity: 1.0},
    {adapter: "keyboard", input: "W", intensity: 1.0},
    {adapter: "keyboard", input: "SPACE", intensity: 1.0}
  ]
```

**Error Handling:**
- If action has zero possible inputs → warn but don't throw
- Return partial capability map with empty slots for unsupported actions
- LLM receives: "jump requires X, but only Y is available"

**Integration Point:**
- Called by Controller Manager on game init or manifest update
- Results cached with TTL (e.g., 5 minutes)
- Cache invalidated on adapter hot-swap

---

### 2. ActionResolver

**Purpose:** Translate abstract actions to concrete device input sequences with fallback chains.

**Inputs:**
- `action_request: ActionRequest` - What the LLM wants to do (e.g., "jump")
- `capability_map: CapabilityMap` - Available device options
- `game_context: GameContext` - Game-specific overrides/preferences
- `adapter_state: AdapterState` - Current device availability

**Outputs:**
- `execution_plan: ExecutionPlan` - Concrete input sequence (primary + fallbacks)

**Logic:**
```
1. Validate action exists in capability_map
2. Get LLM's preferred device (or use game default)
3. Build execution plan with primary and fallback chains:
   - Primary: first choice
   - Fallback 1: alternative device
   - Fallback 2: degraded mode (e.g., simulate with keyboard)
   - Fallback 3: auto-calibrate + retry

4. Example execution plan for "jump":
   {
     "action": "jump",
     "primary": {adapter: "gamepad", input: "A", ...},
     "fallbacks": [
       {adapter: "keyboard", input: "W", ...},
       {adapter: "keyboard", input: "SPACE", ...},
       {adapter: "mouse", input: "click_center", ...}
     ]
   }
```

**Error Handling:**
- If LLM's preference unavailable → warn and use fallback
- Never skip fallback chains; always provide complete plan
- If zero fallbacks possible → return "degraded_mode" with explanation

---

### 3. ControllerManager

**Purpose:** Orchestrate adapters, manage state, handle latency budgets, broadcast events.

**Key Methods:**

```python
def initialize(game_manifest: GameManifest):
    """Setup for new game."""
    - Load game manifest
    - Call capability negotiator
    - Cache capability map
    - Broadcast game_initialized event

def execute_action(action_request: ActionRequest) -> ActionResult:
    """Execute action with graceful degradation."""
    - Get execution plan from ActionResolver
    - Measure latency budget
    - Try primary → fallback 1 → fallback 2 → etc.
    - Broadcast action_executed event
    - Return rich result (success/failure/fallback-used/why)

def get_adapter_state() -> Dict[str, AdapterState]:
    """Current state of all adapters."""
    - Query each adapter for: available, latency, config_status
    - Return aggregated state

def calibrate_adapter(adapter_name: str):
    """Recalibrate single adapter."""
    - Call adapter.calibrate()
    - Broadcast adapter_calibrated event
    - Cache result

def set_latency_budget(action: str, budget_ms: int):
    """Update latency budget for specific action."""
    - Store in action-specific config
    - Adapters throttle if needed
```

**State Management:**
- Per-adapter state (latency, last-used-time, calibration-status)
- Global state (current-game, latency-budgets, adapter-availability)
- Event broadcast on every state change

**Latency Handling:**
- Game specifies budget: `latency_budget_ms: 50`
- ControllerManager measures actual latency
- If exceeds budget → log warning, try faster fallback
- Adapters implement throttling (skip frames, reduce precision)

---

### 4. Adapter Base & Implementations

#### Adapter Interface (Abstract)

```python
class Adapter(ABC):
    """Base class for all input adapters."""
    
    @property
    def name(self) -> str:
        """Unique adapter identifier."""
    
    @property
    def is_available(self) -> bool:
        """Can this adapter be used right now?"""
    
    def get_capabilities(self) -> AdapterCapabilities:
        """What inputs does this adapter support?"""
    
    async def press(self, input_id: str, duration_ms: int, intensity: float) -> ActionResult:
        """Press/activate an input."""
    
    async def release(self, input_id: str) -> ActionResult:
        """Release a held input."""
    
    async def calibrate(self) -> CalibrationResult:
        """Recalibrate adapter (test all inputs, measure latency, etc.)."""
    
    def get_state(self) -> AdapterState:
        """Current state: available, latency, calibration_status, last_action."""
```

#### GamepadAdapter

**Supported Inputs:** A, B, X, Y, LB, RB, LT, RT, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, LS, RS

**Implementation:**
- Uses `pygame.joystick` or `xinput` library (Windows) or `evdev` (Linux)
- Detects connected gamepads on init
- Supports intensity (0.0-1.0) for analog triggers
- Graceful degradation if gamepad disconnected

**Calibration:**
- Tests each button (press & release)
- Measures latency for each input
- Detects stick drift
- Records baseline intensity response

#### KeyboardAdapter

**Supported Inputs:** A-Z, 0-9, SPACE, ENTER, SHIFT, CTRL, ALT, ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT, etc.

**Implementation:**
- Uses `pynput` library (cross-platform)
- Listens to global keyboard events
- Supports key combinations (SHIFT+A, CTRL+C, etc.)

**Calibration:**
- Tests each key mapping
- Measures OS keystroke latency
- Verifies no key conflicts with system

#### MouseAdapter

**Supported Inputs:** MOVE, CLICK_LEFT, CLICK_RIGHT, CLICK_CENTER, SCROLL_UP, SCROLL_DOWN, DRAG

**Implementation:**
- Uses `pynput` for mouse control
- Supports relative and absolute positioning
- Implements drag operations (press + move + release)

**Calibration:**
- Measures click latency
- Tests screen boundary conditions
- Verifies coordinate system

---

## Data Structures & Message Types

### GameManifest

```python
@dataclass
class GameManifest:
    """Game's capability requirements and preferences."""
    
    game_id: str
    game_name: str
    version: str
    
    # Required actions (what the game needs Mimi to do)
    required_actions: List[ActionSpec]
    
    # Device preferences
    preferred_devices: List[str]  # ["gamepad", "keyboard", "mouse"]
    device_priority: Dict[str, int]  # {"gamepad": 1, "keyboard": 2}
    
    # Performance constraints
    latency_budget_ms: Dict[str, int]  # {"jump": 50, "walk": 100}
    max_concurrent_inputs: int
    
    # Game-specific action mappings (override defaults)
    action_overrides: Dict[str, ActionOverride]
```

### ActionSpec

```python
@dataclass
class ActionSpec:
    """Single action requirement."""
    
    action_id: str  # "jump", "walk", "aim"
    action_type: str  # "instant", "hold", "analog"
    description: str
    intensity_required: bool  # Does this action support intensity variation?
    duration_ms: Optional[int]  # For hold actions
```

### CapabilityMap

```python
@dataclass
class CapabilityMap:
    """Mapping of actions to possible device inputs."""
    
    game_id: str
    mapping: Dict[str, List[InputOption]]  # action_id → [option1, option2, ...]
    generated_at: datetime
    cache_ttl_seconds: int
    
    def get_options(self, action_id: str) -> List[InputOption]:
        """Get all possible inputs for an action."""
        return self.mapping.get(action_id, [])
```

### InputOption

```python
@dataclass
class InputOption:
    """Single way to perform an action."""
    
    adapter_name: str  # "gamepad", "keyboard", "mouse"
    input_id: str  # "A", "W", "LEFT_CLICK"
    intensity: float  # 0.0-1.0 (0=binary, 1=full analog)
    duration_ms: Optional[int]  # For hold actions
    priority: int  # Lower = higher priority
```

### ActionRequest

```python
@dataclass
class ActionRequest:
    """LLM's request to perform an action."""
    
    action_id: str
    game_id: str
    latency_budget_ms: int
    preferred_device: Optional[str]  # LLM's preference
    intensity: float  # 0.0-1.0 (if action supports it)
    duration_ms: Optional[int]  # For hold actions
    timestamp: datetime
```

### ExecutionPlan

```python
@dataclass
class ExecutionPlan:
    """Concrete plan to execute an action."""
    
    action_id: str
    primary: ConcreteAction
    fallbacks: List[ConcreteAction]
    estimated_latency_ms: int
    timeout_ms: int
```

### ConcreteAction

```python
@dataclass
class ConcreteAction:
    """Concrete device input to execute."""
    
    adapter_name: str
    input_id: str
    duration_ms: int
    intensity: float
    sequence_order: int  # For multi-step actions (drag = move + click + release)
```

### ActionResult

```python
@dataclass
class ActionResult:
    """Result of executing an action."""
    
    action_id: str
    status: str  # "success", "failed", "degraded", "timeout"
    device_used: str
    input_used: str
    actual_latency_ms: int
    fallback_used: bool
    fallback_reason: Optional[str]
    error_details: Optional[str]
    timestamp: datetime
```

### AdapterState

```python
@dataclass
class AdapterState:
    """Current state of a single adapter."""
    
    adapter_name: str
    is_available: bool
    last_action_time: Optional[datetime]
    last_action_latency_ms: Optional[int]
    calibration_status: str  # "uncalibrated", "calibrated", "drift_detected"
    last_calibration_time: Optional[datetime]
    error_count: int
    config_valid: bool
```

### AdapterCapabilities

```python
@dataclass
class AdapterCapabilities:
    """What a single adapter can do."""
    
    adapter_name: str
    supported_inputs: List[str]  # ["A", "B", "X", "Y", ...]
    supports_intensity: bool
    supports_duration: bool
    supports_sequences: bool
    calibration_available: bool
    estimated_latency_ms: int
    max_concurrent_inputs: int
```

---

## Error Handling & Fallback Strategy

### Core Principle: Never Throw Errors

Every operation returns a result with explicit status. The system gracefully degrades:

```
Try Primary → If fails, try Fallback 1 → If fails, try Fallback 2 → etc.
↓
If ALL fail → Return "degraded" status + rich explanation
↓
Never: throw exception or crash
Always: broadcast state + log + provide feedback to LLM
```

### Fallback Chain for Actions

```
Level 1 (Primary):        Use LLM's preferred device
                          ↓ (if fails)
Level 2 (Game Default):   Use game's preferred device
                          ↓ (if fails)
Level 3 (Alternative):    Try next-priority device
                          ↓ (if fails)
Level 4 (Degraded Mode):  Simulate using different action
                          (e.g., "jump" via keyboard instead of gamepad)
                          ↓ (if fails)
Level 5 (Auto-Calibrate): Re-calibrate adapter + retry once
                          ↓ (if fails)
Level 6 (Result):         Return "degraded" status + rich error info
```

### Error Types & Handling

| Error | Cause | Handling |
|-------|-------|----------|
| `AdapterUnavailable` | Device disconnected | Try fallback adapter |
| `InputNotSupported` | Device doesn't have required input | Try alternative action |
| `LatencyExceeded` | Operation took too long | Log warning, try faster fallback |
| `CalibrationFailed` | Device needs recalibration | Trigger auto-calibrate, retry |
| `ConfigInvalid` | Device config broken | Reset to defaults, try again |
| `ActionNotMapped` | No mapping for this action | Return "degraded" + explanation |

### Rich Feedback on Failure

Every failure includes:

```python
{
    "status": "degraded",
    "action_requested": "jump",
    "reason": "Gamepad button A not responding",
    "what_happened": [
        "Tried gamepad.A → no response (timeout after 50ms)",
        "Tried keyboard.W → success (latency: 45ms)",
        "Action completed via fallback device"
    ],
    "device_used": "keyboard",
    "input_used": "W",
    "fallback_used": true,
    "recommendation": "Re-calibrate gamepad or reconnect device",
    "timestamp": "2026-03-27T14:23:45.123Z"
}
```

---

## Game Manifest Format & Runtime API

### Game Manifest File (YAML/JSON)

**File Location:** `game_manifests/{game_id}/manifest.yaml`

```yaml
game:
  id: platformer_v1
  name: "Super Platformer"
  version: "1.0.0"

capabilities:
  devices:
    - gamepad
    - keyboard
    - mouse
  
  device_priority:
    gamepad: 1
    keyboard: 2
    mouse: 3

actions:
  jump:
    type: instant
    description: "Make character jump"
    supports_intensity: false
    latency_budget_ms: 50
  
  move:
    type: analog
    description: "Move character (X/Y axis)"
    supports_intensity: true
    latency_budget_ms: 100
  
  aim:
    type: analog
    description: "Aim weapon (X/Y axis)"
    supports_intensity: true
    latency_budget_ms: 150

performance:
  max_concurrent_inputs: 2
  max_latency_ms: 200

overrides:
  jump:
    device: gamepad  # Force gamepad if available
    input: A
    duration_ms: 100

  move:
    device: gamepad  # Force gamepad if available
    input: LSTICK    # Left analog stick
```

### Runtime API (Python)

```python
# Initialize for a game
controller_manager.initialize_game(
    game_id="platformer_v1",
    manifest_path="game_manifests/platformer_v1/manifest.yaml"
)

# Execute action
result = await controller_manager.execute_action(
    ActionRequest(
        action_id="jump",
        game_id="platformer_v1",
        latency_budget_ms=50,
        preferred_device="gamepad"  # LLM's preference
    )
)

# Update latency budget (dynamic)
controller_manager.set_latency_budget("jump", 75)

# Get current state
state = controller_manager.get_adapter_state()

# Recalibrate specific adapter
await controller_manager.calibrate_adapter("gamepad")

# Switch game (clean up old game, initialize new)
controller_manager.switch_game(
    game_id="new_game_v1",
    manifest_path="game_manifests/new_game_v1/manifest.yaml"
)
```

### Event Broadcasting

All state changes broadcast via event bus:

```python
# Events emitted:
event_bus.emit("controller.game_initialized", {
    "game_id": "platformer_v1",
    "timestamp": datetime.now()
})

event_bus.emit("controller.action_executed", {
    "action_id": "jump",
    "status": "success",
    "device_used": "gamepad",
    "latency_ms": 32
})

event_bus.emit("controller.adapter_state_changed", {
    "adapter_name": "gamepad",
    "is_available": False,  # Disconnected
    "timestamp": datetime.now()
})

event_bus.emit("controller.adapter_calibrated", {
    "adapter_name": "gamepad",
    "result": "success",
    "timestamp": datetime.now()
})
```

---

## Integration with Execution Brain

### Action Router Extension

**File:** `agent/output/actions.py`

New action handler:

```python
@action_handler("controller_action")
async def handle_controller_action(request: Dict) -> Dict:
    """
    Route controller actions to ControllerManager.
    
    Request format:
    {
        "action_type": "controller_action",
        "action_id": "jump",
        "game_id": "platformer_v1",
        "preferred_device": "gamepad",  # LLM preference
        "intensity": 1.0,
        "duration_ms": 100
    }
    """
    controller_manager = get_controller_manager()
    
    result = await controller_manager.execute_action(
        ActionRequest(
            action_id=request["action_id"],
            game_id=request["game_id"],
            preferred_device=request.get("preferred_device"),
            intensity=request.get("intensity", 1.0),
            duration_ms=request.get("duration_ms"),
            latency_budget_ms=request.get("latency_budget_ms", 100)
        )
    )
    
    return result.to_dict()
```

### Execution Brain Context Injection

When LLM processes a game, inject capability map:

```python
# In execution_brain.py, when initializing LLM prompt:

capability_map = controller_manager.get_capability_map(game_id)

# Build capability context for LLM:
capability_context = """
Available actions for this game:
- jump: gamepad.A OR keyboard.W OR keyboard.SPACE
- move_left: gamepad.LSTICK_LEFT OR keyboard.A
- move_right: gamepad.LSTICK_RIGHT OR keyboard.D
- aim: gamepad.RSTICK OR mouse.MOVE
"""

# Inject into LLM system prompt
llm_context = {
    "game_id": game_id,
    "available_actions": capability_context,
    "device_status": controller_manager.get_adapter_state(),
    "latency_budgets": capability_map.latency_budgets
}
```

### Event Bus Integration

ControllerManager subscribes to/emits events:

```python
# In controller_manager.py:

# Subscribe to adapter events
event_bus.subscribe("controller.adapter_state_changed", 
    on_adapter_state_changed)
event_bus.subscribe("controller.calibration_needed",
    on_calibration_needed)

# Emit events on state changes
event_bus.emit("controller.action_executed", result)
event_bus.emit("controller.adapter_disconnected", adapter_name)
event_bus.emit("controller.latency_exceeded", action_id)

# Execution Brain can react to these:
event_bus.subscribe("controller.adapter_disconnected",
    lambda event: log_warning(f"Device unavailable: {event}"))
```

---

## Implementation Phases

### Phase 1: Core Adapters & Infrastructure (3 tasks)

1. **Setup Controller Module Structure**
   - Create `agent/controller/` directory
   - Create `__init__.py`, `types.py`, `adapter_base.py`
   - Define all data structures (GameManifest, ActionRequest, etc.)

2. **Implement GamepadAdapter**
   - Implement Adapter base class methods
   - Support all gamepad inputs (A, B, X, Y, LB, RB, LT, RT, DPAD, sticks)
   - Implement press(), release(), calibrate(), get_state()
   - Add device detection and graceful disconnection handling

3. **Implement KeyboardAdapter & MouseAdapter**
   - Implement KeyboardAdapter with key/modifier support
   - Implement MouseAdapter with click/move/drag support
   - Both inherit from Adapter base class
   - Test cross-platform functionality

### Phase 2: Orchestration Components (2 tasks)

4. **Implement CapabilityNegotiator**
   - Parse game manifests
   - Query adapters for capabilities
   - Build capability maps
   - Handle caching and TTL

5. **Implement ActionResolver & ControllerManager**
   - Implement ActionResolver (primary + fallback chains)
   - Implement ControllerManager (init, execute, calibrate, state management)
   - Implement event broadcasting
   - Add latency budget handling

### Phase 3: Integration with Execution Brain (2 tasks)

6. **Extend Action Router & Add Event Handlers**
   - Add `controller_action` handler to `actions.py`
   - Create adapter for action routing
   - Implement event subscriptions in ControllerManager

7. **Integration Tests & Documentation**
   - Test full pipeline: game init → action execution → result
   - Test fallback chains
   - Test error handling
   - Document game manifest format
   - Document runtime API

---

## Future Extensibility

### Adding New Input Devices (Example: VR Controllers)

1. Create `VRControllerAdapter` inheriting from `Adapter`
2. Implement required methods (press, release, calibrate, get_state)
3. Register in `agent/config.py` adapter registry
4. CapabilityNegotiator automatically discovers it
5. Games can specify VR controllers in manifest
6. No changes to core orchestration logic needed

### Supporting New Action Types

1. Add action type to `ActionSpec` (e.g., `type: "gesture"`)
2. Adapters that support it implement gesture methods
3. Manifest specifies gesture requirements
4. ActionResolver handles gesture-to-input translation
5. No changes to adapter interface needed

---

## Success Criteria

- ✅ All adapters implement complete Adapter interface
- ✅ CapabilityNegotiator correctly maps game actions to device inputs
- ✅ ActionResolver builds valid fallback chains
- ✅ ControllerManager executes without throwing errors
- ✅ All failures return rich feedback with fallback info
- ✅ Events broadcast on every state change
- ✅ Latency budgets respected (or logged as warnings)
- ✅ Adapters gracefully handle disconnection/recalibration
- ✅ Integration with Execution Brain transparent to LLM
- ✅ Game manifest format supports all required capabilities
- ✅ Runtime API provides complete control

---

## References

- **Execution Brain:** `agent/execution_brain.py`
- **Action Router:** `agent/output/actions.py`
- **Event Bus:** `agent/core/event_bus.py`
- **Configuration:** `agent/config.py`
- **Project Structure:** `docs/PROJECT_STRUCTURE.md`

