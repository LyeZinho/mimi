# Brain Health Check System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement an automatic health check system that tests each of the 7 brains on startup and logs their operational status.

**Architecture:** 
- Create a `BrainHealthCheck` class that instantiates each brain with minimal config and runs a lightweight verification test
- Each brain gets a dedicated async health check method that returns status (operational/failed + reason)
- Main.py calls health check after Orchestrator initialization, logs results, continues only if all pass or logs warnings if any fail
- Health checks run in parallel with configurable timeout per brain

**Tech Stack:** asyncio, logging, pytest for unit tests

---

## Task 1: Create BrainHealthCheck Class

**Files:**
- Create: `agent/core/health_check.py`
- Modify: None yet
- Test: `tests/unit/test_brain_health_check.py`

**Step 1: Write failing test for BrainHealthCheck initialization**

```python
# tests/unit/test_brain_health_check.py
import pytest
from agent.core.health_check import BrainHealthCheck
from agent.core.messaging import EventBus

@pytest.mark.asyncio
async def test_brain_health_check_init():
    """BrainHealthCheck should initialize with EventBus reference."""
    bus = EventBus()
    health_check = BrainHealthCheck(bus)
    assert health_check.bus is bus
    assert health_check.results == {}
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_brain_health_check.py::test_brain_health_check_init -v
```

Expected: `ModuleNotFoundError: No module named 'agent.core.health_check'`

**Step 3: Create minimal BrainHealthCheck class**

```python
# agent/core/health_check.py
"""Brain health check system for startup verification."""

import asyncio
import logging
from typing import Dict, Literal
from agent.core.messaging import EventBus

logger = logging.getLogger(__name__)

Status = Literal["operational", "failed", "timeout"]


class BrainHealthCheck:
    """Health check system for all 7 brains."""

    def __init__(self, bus: EventBus):
        """Initialize with EventBus reference."""
        self.bus = bus
        self.results: Dict[str, Dict] = {}

    async def run(self, timeout: int = 10) -> bool:
        """Run all brain health checks. Returns True if all operational."""
        raise NotImplementedError
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_brain_health_check.py::test_brain_health_check_init -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agent/core/health_check.py tests/unit/test_brain_health_check.py
git commit -m "feat: create BrainHealthCheck class skeleton"
```

---

## Task 2: Implement Individual Brain Health Check Methods

**Files:**
- Modify: `agent/core/health_check.py`
- Modify: `agent/brains/input_brain.py` (add `async def health_check()` method)
- Modify: `agent/brains/reasoning_brain.py` (add health check)
- Modify: `agent/brains/planning_brain.py` (add health check)
- Modify: `agent/brains/execution_brain.py` (add health check)
- Modify: `agent/brains/sentiment_brain.py` (add health check)
- Modify: `agent/brains/avatar_brain.py` (add health check)
- Modify: `agent/brains/output_brain.py` (add health check)
- Test: `tests/unit/test_brain_health_check.py` (add tests for each brain)

**Step 1: Add health check method to InputBrain**

```python
# In agent/brains/input_brain.py, add this method to InputBrain class:

async def health_check(self) -> dict:
    """
    Verify InputBrain is operational.
    
    Returns:
        {
            "name": "InputBrain",
            "status": "operational" | "failed" | "timeout",
            "details": "description of status"
        }
    """
    try:
        # Test 1: VAD engine initialized
        if self.vad_engine is None:
            return {"name": "InputBrain", "status": "failed", "details": "VAD engine not initialized"}
        
        # Test 2: STT engine initialized
        if self.stt_engine is None:
            return {"name": "InputBrain", "status": "failed", "details": "STT engine not initialized"}
        
        # Test 3: Buffer manager initialized
        if self.buffer_manager is None:
            return {"name": "InputBrain", "status": "failed", "details": "Buffer manager not initialized"}
        
        # Test 4: Event bus subscription exists
        if not hasattr(self, 'bus') or self.bus is None:
            return {"name": "InputBrain", "status": "failed", "details": "EventBus not attached"}
        
        return {"name": "InputBrain", "status": "operational", "details": "All components initialized"}
    except Exception as e:
        return {"name": "InputBrain", "status": "failed", "details": str(e)}
```

**Step 2: Add health check method to ReasoningBrain**

```python
# In agent/brains/reasoning_brain.py, add:

async def health_check(self) -> dict:
    """Verify ReasoningBrain is operational."""
    try:
        # Test 1: LLM provider initialized
        if self.llm_provider is None:
            return {"name": "ReasoningBrain", "status": "failed", "details": "LLM provider not initialized"}
        
        # Test 2: Event bus attached
        if not hasattr(self, 'bus') or self.bus is None:
            return {"name": "ReasoningBrain", "status": "failed", "details": "EventBus not attached"}
        
        # Test 3: Try a simple LLM connection test
        try:
            # Call validate_connection (should be quick)
            is_valid = await asyncio.wait_for(
                self.llm_provider.validate_connection(),
                timeout=5.0
            )
            if not is_valid:
                return {"name": "ReasoningBrain", "status": "failed", "details": "LLM connection validation failed"}
        except asyncio.TimeoutError:
            return {"name": "ReasoningBrain", "status": "timeout", "details": "LLM connection timeout"}
        
        return {"name": "ReasoningBrain", "status": "operational", "details": "LLM provider operational"}
    except Exception as e:
        return {"name": "ReasoningBrain", "status": "failed", "details": str(e)}
```

**Step 3: Add health check methods to remaining brains (PlanningBrain, ExecutionBrain, SentimentBrain, AvatarBrain, OutputBrain)**

Each follows the same pattern:

```python
async def health_check(self) -> dict:
    """Verify [BrainName] is operational."""
    try:
        # Check essential components are initialized
        if not hasattr(self, 'bus') or self.bus is None:
            return {"name": "[BrainName]", "status": "failed", "details": "EventBus not attached"}
        
        # Brain-specific checks:
        # PlanningBrain: check planner/strategy engine
        # ExecutionBrain: check executor/task queue
        # SentimentBrain: check sentiment analyzer
        # AvatarBrain: check avatar interface
        # OutputBrain: check output handler (TTS/action dispatcher)
        
        return {"name": "[BrainName]", "status": "operational", "details": "All components initialized"}
    except Exception as e:
        return {"name": "[BrainName]", "status": "failed", "details": str(e)}
```

**Step 4: Update BrainHealthCheck to call all brain health checks**

```python
# In agent/core/health_check.py, update run() method:

async def run(self, brains: Dict[str, Brain], timeout: int = 10) -> bool:
    """
    Run all brain health checks in parallel.
    
    Args:
        brains: Dict mapping brain names to brain instances
        timeout: Seconds to wait per brain before timing out
    
    Returns:
        True if all brains operational, False if any failed/timed out
    """
    self.results = {}
    
    # Create tasks for all brain health checks
    tasks = {
        name: asyncio.create_task(
            asyncio.wait_for(brain.health_check(), timeout=timeout)
        )
        for name, brain in brains.items()
    }
    
    # Gather all results
    try:
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for brain_name, result in zip(tasks.keys(), results):
            if isinstance(result, asyncio.TimeoutError):
                self.results[brain_name] = {
                    "name": brain_name,
                    "status": "timeout",
                    "details": f"Health check timed out after {timeout}s"
                }
            elif isinstance(result, Exception):
                self.results[brain_name] = {
                    "name": brain_name,
                    "status": "failed",
                    "details": str(result)
                }
            else:
                self.results[brain_name] = result
    except Exception as e:
        logger.error(f"Critical error during health check: {e}")
        return False
    
    # Log results
    for brain_name, result in self.results.items():
        status = result.get("status", "unknown")
        details = result.get("details", "")
        if status == "operational":
            logger.info(f"✓ {brain_name:20} operational - {details}")
        elif status == "timeout":
            logger.warning(f"⚠ {brain_name:20} timeout - {details}")
        else:
            logger.error(f"✗ {brain_name:20} failed - {details}")
    
    # Check if all operational
    all_operational = all(
        result.get("status") == "operational"
        for result in self.results.values()
    )
    
    return all_operational
```

**Step 5: Write tests for health check**

```python
# In tests/unit/test_brain_health_check.py:

@pytest.mark.asyncio
async def test_health_check_all_brains():
    """Health check should verify all brains are operational."""
    from agent.orchestrator import AgentOrchestrator
    from agent.llm.ollama_provider import OllamaProvider
    
    # Create minimal orchestrator
    llm_provider = OllamaProvider()
    orchestrator = AgentOrchestrator(llm_provider=llm_provider)
    
    # Create health check
    bus = orchestrator.bus
    health_check = BrainHealthCheck(bus)
    
    # Run health checks
    brains = {
        "InputBrain": orchestrator.input_brain,
        "ReasoningBrain": orchestrator.reasoning_brain,
        "PlanningBrain": orchestrator.planning_brain,
        "ExecutionBrain": orchestrator.execution_brain,
        "SentimentBrain": orchestrator.sentiment_brain,
        "AvatarBrain": orchestrator.avatar_brain,
        "OutputBrain": orchestrator.output_brain,
    }
    
    results = await health_check.run(brains, timeout=5)
    
    # Verify all brains checked
    assert len(health_check.results) == 7
    
    # Verify each has status
    for brain_name, result in health_check.results.items():
        assert "status" in result
        assert result["status"] in ["operational", "failed", "timeout"]
        assert "details" in result
```

**Step 6: Run tests**

```bash
pytest tests/unit/test_brain_health_check.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add agent/core/health_check.py \
        agent/brains/*.py \
        tests/unit/test_brain_health_check.py
git commit -m "feat: add health check methods to all 7 brains"
```

---

## Task 3: Integrate Health Check into main.py

**Files:**
- Modify: `agent/main.py` (call health check after initialization)
- Test: `tests/integration/test_health_check_startup.py` (new)

**Step 1: Update main.py to call health check**

```python
# In agent/main.py, after orchestrator initialization (around line 70):

import asyncio
from agent.core.health_check import BrainHealthCheck

async def main():
    """Main entry point for Mimi agent."""
    
    logger.info("🚀 Starting Mimi Agent Orchestrator...")
    
    # ... existing setup code ...
    
    # Initialize Orchestrator
    logger.info("Initializing 7-brain Orchestrator...")
    orchestrator = AgentOrchestrator(
        llm_provider=llm_provider,
        input_brain=None,  # Auto-create
        # ... other params
    )
    
    # ===== NEW: Health Check =====
    logger.info("Running brain health checks...")
    health_check = BrainHealthCheck(orchestrator.bus)
    
    brains = {
        "InputBrain": orchestrator.input_brain,
        "ReasoningBrain": orchestrator.reasoning_brain,
        "PlanningBrain": orchestrator.planning_brain,
        "ExecutionBrain": orchestrator.execution_brain,
        "SentimentBrain": orchestrator.sentiment_brain,
        "AvatarBrain": orchestrator.avatar_brain,
        "OutputBrain": orchestrator.output_brain,
    }
    
    all_operational = await health_check.run(brains, timeout=10)
    
    if all_operational:
        logger.info("✅ All brains operational - Agent ready")
    else:
        logger.warning("⚠️ Some brains failed health check - starting with warnings")
    
    # ===== END Health Check =====
    
    # Initialize Bridge
    logger.info("Initializing OrchestratorBridge...")
    bridge = OrchestratorBridge(orchestrator, ws_uri="ws://localhost:8765")
    
    # ... rest of startup ...
```

**Step 2: Write integration test**

```python
# tests/integration/test_health_check_startup.py
import pytest
from agent.main import main
from agent.core.health_check import BrainHealthCheck

@pytest.mark.asyncio
async def test_orchestrator_startup_with_health_check(monkeypatch):
    """Verify Orchestrator initializes and passes health check on startup."""
    # This test ensures main.py health check runs without errors
    # Note: Full integration test would require mocking WebSocket
    
    # Mock the EventBus.start() and WebSocket connection
    startup_called = []
    
    async def mock_start():
        startup_called.append(True)
    
    from agent.orchestrator import AgentOrchestrator
    from agent.llm.ollama_provider import OllamaProvider
    
    llm_provider = OllamaProvider()
    orchestrator = AgentOrchestrator(llm_provider=llm_provider)
    
    health_check = BrainHealthCheck(orchestrator.bus)
    
    brains = {
        "InputBrain": orchestrator.input_brain,
        "ReasoningBrain": orchestrator.reasoning_brain,
        "PlanningBrain": orchestrator.planning_brain,
        "ExecutionBrain": orchestrator.execution_brain,
        "SentimentBrain": orchestrator.sentiment_brain,
        "AvatarBrain": orchestrator.avatar_brain,
        "OutputBrain": orchestrator.output_brain,
    }
    
    # Run health checks (should not raise)
    results = await health_check.run(brains, timeout=10)
    
    # At minimum, all brains should be present
    assert len(health_check.results) == 7
    assert all("status" in result for result in health_check.results.values())
```

**Step 3: Run integration test**

```bash
pytest tests/integration/test_health_check_startup.py -v
```

Expected: PASS

**Step 4: Run full agent startup locally**

```bash
python agent/main.py
```

Expected output:
```
🚀 Starting Mimi Agent Orchestrator...
Initializing 7-brain Orchestrator...
Running brain health checks...
✓ InputBrain            operational - All components initialized
✓ ReasoningBrain        operational - LLM provider operational
✓ PlanningBrain         operational - All components initialized
✓ ExecutionBrain        operational - All components initialized
✓ SentimentBrain        operational - All components initialized
✓ AvatarBrain           operational - All components initialized
✓ OutputBrain           operational - All components initialized
✅ All brains operational - Agent ready
```

**Step 5: Commit**

```bash
git add agent/main.py tests/integration/test_health_check_startup.py
git commit -m "feat: integrate health check into agent startup

Calls BrainHealthCheck.run() after Orchestrator initialization.
Logs individual brain status. Continues startup regardless of failures
but warns user about any issues."
```

---

## Task 4: Add Docker Startup Logging

**Files:**
- Modify: `docker/entrypoint.sh` (log health check output)

**Step 1: Update entrypoint to capture health check logs**

```bash
#!/bin/bash
# docker/entrypoint.sh

set -e

echo "🚀 Mimi Dev Container Starting"
echo "=============================="
echo ""

# Start WebSocket server in background
echo "📡 Starting WebSocket Server..."
node web_avatar/server.js &
WEBSOCKET_PID=$!
echo "✓ WebSocket Server running (PID: $WEBSOCKET_PID)"

# Wait for WebSocket to be ready
sleep 2

# Start Python Agent and capture output with health check logs
echo "🤖 Starting Python Agent..."
python agent/main.py 2>&1 | tee agent_output.log &
AGENT_PID=$!
echo "✓ Python Agent running (PID: $AGENT_PID)"

# Wait for agent to complete health checks (max 15 seconds)
sleep 5

# Check if health checks passed by looking at logs
if grep -q "✅ All brains operational" agent_output.log; then
    echo "✅ Health check passed"
elif grep -q "⚠️ Some brains failed" agent_output.log; then
    echo "⚠️ Health check partial - some brains failed (see logs above)"
else
    echo "⚠️ Health check status unknown (check agent_output.log)"
fi

# Start React Frontend
echo "⚛  Starting React Frontend..."
cd web_avatar && npm run dev &
FRONTEND_PID=$!
echo "✓ React Frontend running (PID: $FRONTEND_PID)"

echo ""
echo "=============================="
echo "✅ All services started!"
echo "=============================="
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "📡 WebSocket: ws://localhost:8765"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep running
wait
```

**Step 2: Test in Docker**

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

Expected output:
```
🚀 Mimi Dev Container Starting
==============================

📡 Starting WebSocket Server...
✓ WebSocket Server running (PID: 8)
🤖 Starting Python Agent...
✓ Python Agent running (PID: 16)
[From agent_output.log...]
✓ InputBrain            operational - All components initialized
✓ ReasoningBrain        operational - LLM provider operational
✓ PlanningBrain         operational - All components initialized
✓ ExecutionBrain        operational - All components initialized
✓ SentimentBrain        operational - All components initialized
✓ AvatarBrain           operational - All components initialized
✓ OutputBrain           operational - All components initialized
✅ Health check passed
⚛  Starting React Frontend...
✓ React Frontend running (PID: 18)

============================
✅ All services started!
============================

🌐 Frontend: http://localhost:5173
📡 WebSocket: ws://localhost:8765

Press Ctrl+C to stop all services
```

**Step 3: Commit**

```bash
git add docker/entrypoint.sh
git commit -m "feat: capture and display health check logs in Docker startup

Docker entrypoint now:
- Starts services
- Waits for health check to complete
- Displays summary: passed/partial/unknown
- Logs full output to agent_output.log"
```

---

## Task 5: Add README Documentation

**Files:**
- Modify: `README.md` (add health check section)

**Step 1: Add health check documentation**

```markdown
## 🏥 Brain Health Check

Every time the agent starts, it automatically verifies that all 7 brains are operational:

```
✓ InputBrain            operational - All components initialized
✓ ReasoningBrain        operational - LLM provider operational
✓ PlanningBrain         operational - All components initialized
✓ ExecutionBrain        operational - All components initialized
✓ SentimentBrain        operational - All components initialized
✓ AvatarBrain           operational - All components initialized
✓ OutputBrain           operational - All components initialized
✅ All brains operational - Agent ready
```

### What's Being Checked

- **InputBrain**: VAD engine, STT engine, buffer manager, EventBus
- **ReasoningBrain**: LLM provider, LLM connection validation
- **PlanningBrain**: Planner initialization
- **ExecutionBrain**: Executor/task queue initialization
- **SentimentBrain**: Sentiment analyzer initialization
- **AvatarBrain**: Avatar interface attachment
- **OutputBrain**: Output handler (TTS, action dispatcher)

### Timeout Behavior

Each brain gets **10 seconds** to complete its health check. If a brain times out or fails:
- **Status**: ⚠️ or ✗
- **Impact**: Agent continues but logs warning
- **Action**: Check logs for specific brain error details

### Viewing Health Check Logs

**Local startup:**
```bash
python agent/main.py
# Look for health check output in console
```

**Docker:**
```bash
docker-compose up
# Health check runs automatically during startup
# Results shown in container logs
```

**Agent log file:**
```bash
tail -f agent_output.log | grep -E "(✓|✗|⚠)" 
```
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add brain health check section to README"
```

---

## Summary

**Total commits:** 5  
**Files created:** 2 (`agent/core/health_check.py`, `tests/integration/test_health_check_startup.py`)  
**Files modified:** 7 (main.py, all 7 brains, entrypoint.sh, README.md)  
**Lines added:** ~400  

**Key Features:**
- ✅ All 7 brains tested individually on startup
- ✅ Parallel health checks with timeout
- ✅ Clear logging: ✓ operational / ⚠ timeout / ✗ failed
- ✅ Docker integration with startup summary
- ✅ No blocking - continues even if some brains fail but warns
- ✅ Detailed error messages for troubleshooting

**Testing:**
- Unit tests for BrainHealthCheck class
- Integration test for startup flow
- Manual testing in local and Docker environments

