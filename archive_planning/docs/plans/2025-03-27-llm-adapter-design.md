"""
LLM Adapter Architecture Design
Date: 2025-03-27
Status: Approved for implementation
"""

# LLM Adapter Architecture: Flexible Provider Abstraction

## 1. Design Overview

### Goals
- **Abstraction**: Unified interface for any LLM provider (Ollama, Gemini, OpenAI, etc.)
- **Extensibility**: Add new providers without changing ReasoningBrain code
- **Local-first**: Start with Ollama, expand to cloud providers as needed
- **Session-level config**: Choose provider at startup, fixed for entire session
- **Streaming + Batch**: Support both response modes seamlessly
- **Usage tracking**: Log tokens for monitoring (no enforcement for MVP)
- **Fail-fast**: Raise errors for calling code to handle

### Architecture Pattern: Strategy Pattern with Inheritance

```
┌─────────────────────────────────────────────────┐
│         ReasoningBrain                          │
│  (owns an LLMProvider instance)                  │
└──────────────────────┬──────────────────────────┘
                       │ uses
                       │
┌──────────────────────▼──────────────────────────┐
│         LLMProvider (abstract base)              │
│  + generate(prompt, stream)                      │
│  + count_tokens(text)                            │
│  + validate_connection()                         │
│  + measure_latency()                             │
└──────────────────────┬──────────────────────────┘
                       │ implements
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌────────┐  ┌─────────┐  ┌──────────┐
    │Ollama  │  │Gemini   │  │OpenAI    │
    │(local) │  │(cloud)  │  │(cloud)   │
    └────────┘  └─────────┘  └──────────┘
```

## 2. Component Specifications

### 2.1 LLMProvider (Abstract Base Class)

**File**: `agent/llm/provider.py`

```python
class LLMProvider(ABC):
    """Abstract base for all LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.token_count = 0  # Track total tokens used
        self.latency_ms = 0.0
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        stream: bool = False
    ) -> Union[str, AsyncIterator[str]]:
        """Generate response from prompt.
        
        Args:
            prompt: Input text
            stream: If True, return async iterator of tokens
                    If False, return complete response string
        
        Returns:
            Full response string OR async iterator of response chunks
        
        Raises:
            LLMProviderError: Connection, timeout, auth, rate limit errors
        """
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Estimate token count (provider-specific)."""
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Test provider connectivity."""
    
    async def measure_latency(self) -> float:
        """Measure first-token latency (optional, base impl)."""
```

**Base implementation provides**:
- Token tracking (counts tokens in/out)
- Streaming wrapper (converts batch → stream if needed)
- Error wrapping (converts provider errors → standardized LLMProviderError)
- Latency measurement
- Response validation

---

### 2.2 Provider Implementations

#### **Ollama Provider** (Local, HTTP API)
**File**: `agent/llm/ollama_provider.py`

```python
class OllamaProvider(LLMProvider):
    """Local LLM via Ollama HTTP API."""
    
    def __init__(self, config: OllamaConfig):
        # config.host: str = "http://localhost:11434"
        # config.model: str = "phi3:mini"
        # config.temperature: float = 0.7
        # config.top_p: float = 0.9
    
    async def generate(self, prompt: str, stream: bool = False):
        # POST /api/generate with stream parameter
        # Returns full text if stream=False
        # Returns token iterator if stream=True
    
    def count_tokens(self, text: str) -> int:
        # Simple tokenizer or use model-specific estimate
```

**Capabilities**:
- ✓ Streaming (native)
- ✓ Batch (native)
- ✓ Local execution (no API keys needed)
- ✓ Token counting (model-specific)
- ✓ Temperature, top_p, context size control

**Error handling**: Connection refused, timeout (5s default)

---

#### **Gemini Provider** (Google Cloud API)
**File**: `agent/llm/gemini_provider.py`

```python
class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""
    
    def __init__(self, config: GeminiConfig):
        # config.api_key: str
        # config.model: str = "gemini-1.5-flash"
    
    async def generate(self, prompt: str, stream: bool = False):
        # google.generativeai.GenerativeModel
        # Streaming: content.stream()
        # Batch: generate_content()
    
    def count_tokens(self, text: str) -> int:
        # Use Gemini's count_tokens API
```

**Capabilities**:
- ✓ Streaming (via google.generativeai)
- ✓ Batch (via google.generativeai)
- ✓ Token counting (native API)
- ✓ Vision models (future)

**Error handling**: Invalid API key, quota exceeded, network timeout

---

#### **OpenAI Provider** (OpenAI API)
**File**: `agent/llm/openai_provider.py`

```python
class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-3.5, GPT-4, etc.)."""
    
    def __init__(self, config: OpenAIConfig):
        # config.api_key: str
        # config.model: str = "gpt-3.5-turbo"
    
    async def generate(self, prompt: str, stream: bool = False):
        # OpenAI Chat Completions API
        # Streaming: stream=True
        # Batch: stream=False
    
    def count_tokens(self, text: str) -> int:
        # Use tiktoken library for accurate counting
```

**Capabilities**:
- ✓ Streaming (native)
- ✓ Batch (native)
- ✓ Token counting (tiktoken)
- ✓ Function calling (future)

**Error handling**: Invalid API key, rate limit, context length exceeded

---

### 2.3 Factory

**File**: `agent/llm/factory.py`

```python
class LLMProviderFactory:
    """Factory for creating LLM providers."""
    
    _providers = {
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
    }
    
    @staticmethod
    async def create(config: LLMConfig) -> LLMProvider:
        """Create and validate provider instance.
        
        Args:
            config: Provider-specific config (LLMConfig base class)
        
        Returns:
            Initialized LLMProvider subclass
        
        Raises:
            LLMProviderError: If provider not found or validation fails
        """
        # 1. Get provider class
        # 2. Instantiate
        # 3. Call validate_connection()
        # 4. Return instance or raise error
```

---

### 2.4 Configuration

**File**: `agent/llm/config.py`

```python
@dataclass
class LLMConfig:
    """Base config for all providers."""
    provider: str  # "ollama" | "gemini" | "openai"
    model: str
    timeout_sec: float = 30.0
    max_retries: int = 0  # No retries (fail-fast)

@dataclass
class OllamaConfig(LLMConfig):
    host: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9

@dataclass
class GeminiConfig(LLMConfig):
    api_key: str = ""  # From env var GEMINI_API_KEY
    # safety_settings, generation_config optional

@dataclass
class OpenAIConfig(LLMConfig):
    api_key: str = ""  # From env var OPENAI_API_KEY
    temperature: float = 0.7
    max_tokens: int = 2048
```

**Loading**: From `.env` file at startup:
```
LLM_PROVIDER=ollama
LLM_MODEL=phi3:mini
OLLAMA_HOST=http://localhost:11434
GEMINI_API_KEY=<key if using gemini>
OPENAI_API_KEY=<key if using openai>
```

---

### 2.5 Error Handling

**File**: `agent/llm/errors.py`

```python
class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""
    pass

class LLMConnectionError(LLMProviderError):
    """Provider unreachable."""
    pass

class LLMAuthError(LLMProviderError):
    """Authentication failed (invalid API key)."""
    pass

class LLMRateLimitError(LLMProviderError):
    """Rate limit exceeded."""
    pass

class LLMTimeoutError(LLMProviderError):
    """Request timeout."""
    pass

class LLMValidationError(LLMProviderError):
    """Response validation failed."""
    pass
```

---

### 2.6 Usage Tracking

**File**: `agent/llm/usage_tracker.py`

```python
@dataclass
class UsageStats:
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    requests: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(1, self.requests)
    
    def log(self):
        """Log summary (for monitoring)."""
        logger.info(
            f"LLM Usage: {self.provider}/{self.model} | "
            f"In:{self.tokens_in} Out:{self.tokens_out} | "
            f"Requests:{self.requests} Errors:{self.errors} | "
            f"Latency:{self.avg_latency_ms:.0f}ms"
        )
```

---

## 3. ReasoningBrain Integration

**File**: `agent/brains/reasoning_brain.py` (modified)

```python
class ReasoningBrain(Brain):
    def __init__(self, *args, llm_provider: LLMProvider, **kwargs):
        super().__init__(*args, **kwargs)
        self.llm = llm_provider
    
    async def _infer_intent(self, transcript: str, context):
        """Use LLM to extract intent from transcript."""
        # Build prompt with transcript + context
        prompt = self._build_prompt(transcript, context)
        
        # Get response (streaming or batch)
        try:
            if self.should_stream:  # Per-request decision
                async for chunk in self.llm.generate(prompt, stream=True):
                    # Publish streaming event
                    await self.publish_event(EventType.INTENT_STREAMING, {...})
            else:
                response = await self.llm.generate(prompt, stream=False)
                # Process complete response
        
        except LLMProviderError as e:
            logger.error(f"LLM error: {e}")
            # Fail-fast: raise, ReasoningBrain doesn't catch
            raise
```

---

## 4. Data Flow

### Happy Path: Transcription → LLM → Intent Event

```
User speaks:
  "Qual é o horário de funcionamento?"
         ↓
[InputBrain] VAD + STT
  TRANSCRIPTION_COMPLETE event
         ↓
[ReasoningBrain] listens for TRANSCRIPTION_COMPLETE
  1. Build prompt: "Extract intent from: 'Qual é o horário...?'"
  2. Call LLM: llm.generate(prompt, stream=True/False)
  3. Parse response: {"intent": "query_hours", "confidence": 0.95}
  4. Publish: INTENT_DETECTED event
         ↓
[PlanningBrain] validates intent
[ExecutionBrain] dispatches tools
[SentimentBrain] detects emotion
[AvatarBrain] plays animation
[OutputBrain] generates TTS response
```

### Error Path: LLM Fails

```
ReasoningBrain calls llm.generate()
         ↓
LLM provider raises LLMTimeoutError
         ↓
ReasoningBrain catches, logs, re-raises (fail-fast)
         ↓
Orchestrator logs the error
         ↓
User sees "Sorry, connection error" (via OutputBrain fallback)
```

---

## 5. File Structure

```
agent/llm/
├── __init__.py
├── provider.py           # Abstract base class
├── config.py            # Configuration dataclasses
├── errors.py            # Exception hierarchy
├── factory.py           # LLMProviderFactory
├── usage_tracker.py     # Token/latency tracking
│
├── ollama_provider.py   # Ollama implementation
├── gemini_provider.py   # Gemini implementation (future)
├── openai_provider.py   # OpenAI implementation (future)
│
├── prompt_templates.py  # Intent extraction prompts
└── tests/
    ├── test_provider.py
    ├── test_factory.py
    ├── test_ollama_provider.py
    └── test_providers_e2e.py
```

---

## 6. Testing Strategy

### Unit Tests
- **test_provider.py**: Mock LLMProvider, verify interface
- **test_factory.py**: Verify factory creates correct provider
- **test_ollama_provider.py**: Mock Ollama HTTP, test generate/count_tokens

### Integration Tests
- **test_providers_e2e.py**: Real Ollama instance (Docker), test streaming + batch

### Mocking Strategy
```python
class MockLLMProvider(LLMProvider):
    """For testing ReasoningBrain without real LLM."""
    async def generate(self, prompt, stream=False):
        return "mocked response"
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Day 1)
- [x] Abstract LLMProvider base class
- [x] Configuration system
- [x] Error hierarchy
- [x] Factory with validation

### Phase 2: Ollama (Day 1-2)
- [ ] OllamaProvider implementation
- [ ] Streaming + batch support
- [ ] Token counting
- [ ] HTTP client (aiohttp)
- [ ] Unit tests

### Phase 3: ReasoningBrain Integration (Day 2)
- [ ] Inject LLMProvider into ReasoningBrain
- [ ] Implement _infer_intent using LLM
- [ ] Prompt templates
- [ ] Integration tests

### Phase 4: Extensibility (Future)
- [ ] GeminiProvider
- [ ] OpenAIProvider
- [ ] Provider auto-detection
- [ ] Usage dashboard

---

## 8. Success Criteria

✓ Unified interface works for any provider
✓ Adding new provider = 1 class file + tests
✓ ReasoningBrain agnostic to provider choice
✓ Streaming + batch work seamlessly
✓ Token tracking visible in logs
✓ Fail-fast error handling
✓ All tests pass
✓ < 150ms latency end-to-end (STT → LLM → Intent event)

---

## 9. Design Decisions Rationale

| Decision | Why |
|----------|-----|
| **Strategy Pattern** | Each provider self-contained, shared base reduces duplication |
| **Session-level config** | Simpler for MVP, good enough for now, can add request-level later |
| **Streaming + Batch** | Some use cases need real-time (streaming), others need batching for accuracy |
| **Fail-fast errors** | ReasoningBrain decides how to handle errors (retry, fallback, etc.) |
| **Token tracking only** | No cost enforcement yet, just visibility for now |
| **Local-first Ollama** | Free, no API keys, works offline, perfect for development |

---

## 10. Future Extensions (Not in MVP)

- [ ] Request-level provider switching (e.g., fallback to OpenAI if Ollama down)
- [ ] Cost limits and alerts
- [ ] Provider performance dashboard
- [ ] Model selection by capability (e.g., "find provider with vision support")
- [ ] Prompt optimization (e.g., Claude's "thinking" models)
- [ ] Function calling integration
- [ ] Fine-tuned models per use case
