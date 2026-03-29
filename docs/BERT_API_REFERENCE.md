# BERT Sentiment Engine - API Reference

## Classes

### BertSentimentEngine

```python
from agent.sentiment.bert_engine import BertSentimentEngine
```

#### Constructor

```python
BertSentimentEngine(
    model_path: Optional[Path] = None,
    device: str = "cpu"
) -> BertSentimentEngine
```

**Parâmetros**:

- `model_path` (Optional[Path]): Caminho para diretório do modelo
  - Default: `{repo_root}/sentiment-model/`
  - Type: `pathlib.Path` ou `None`
  
- `device` (str): Dispositivo para executar modelo
  - Default: `"cpu"`
  - Valores: `"cpu"`, `"cuda"`, `"mps"`
  - Note: GPU requer CUDA/PyTorch com suporte

**Retorno**: Instance of `BertSentimentEngine`

**Exemplo**:

```python
# Default (CPU)
engine = BertSentimentEngine()

# Custom path
from pathlib import Path
custom_model = Path("/data/custom-bert-model")
engine = BertSentimentEngine(model_path=custom_model)

# GPU (if available)
engine = BertSentimentEngine(device="cuda")
```

---

#### initialize()

```python
async def initialize(self) -> None
```

Carrega tokenizer e modelo do disco.

**Comportamento**:

1. Log: `"Loading FinBERT-PT-BR model from {path}..."`
2. Carrega tokenizer de `{model_path}/tokenizer.json`
3. Carrega modelo de `{model_path}/pytorch_model.bin`
4. Move modelo para device (CPU/GPU)
5. Set modelo em modo `eval()`
6. Seta `self._initialized = True`
7. Log: `"FinBERT-PT-BR model loaded successfully"`

**Exceções**:

- `FileNotFoundError`: Se `pytorch_model.bin` não existe
- `transformers.utils.RepositoryNotFoundError`: Se arquivo corrompido
- `torch.cuda.OutOfMemoryError`: Se GPU memory insuficiente

**Raises**: `Exception` em caso de erro (caller deve tratar)

**Tempo**: ~2-5 segundos (primeira vez), ~1-2s (cache quente)

**Exemplo**:

```python
engine = BertSentimentEngine(device="cpu")

try:
    await engine.initialize()
    print("✓ Model loaded")
except Exception as e:
    print(f"✗ Failed: {e}")
    # Handle error - use fallback
```

---

#### analyze(text: str)

```python
async def analyze(self, text: str) -> dict
```

Analisa sentimento de um texto.

**Parâmetros**:

- `text` (str): Texto português para análise
  - Min: 1 caractere
  - Max: Qualquer (truncado em 512 tokens)
  - Encoding: UTF-8

**Retorno**: `dict` com estrutura:

```python
{
    "sentiment": str,      # "happy" | "sad" | "neutral"
    "confidence": float,   # 0.0 - 1.0 (softmax score)
    "label": str,         # "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    "logits": list,       # [pos_score, neg_score, neutral_score]
}
```

**Detalhes de retorno**:

- `sentiment`: Mapeamento user-friendly
  - 0 (POSITIVE) → `"happy"`
  - 1 (NEGATIVE) → `"sad"`
  - 2 (NEUTRAL) → `"neutral"`

- `confidence`: Softmax score da classe predita (0-1)
  - 0.95 = modelo 95% confiante
  - 0.50 = modelo 50% confiante (ambíguo)

- `label`: Rótulo bruto do modelo (BERT padrão)

- `logits`: Scores brutos antes de softmax
  - [3.2, -1.1, 0.5] → POSITIVE tem score mais alto
  - Útil para debugging

**Comportamento**:

1. Se não inicializado → retorna fallback `{sentiment: "neutral", confidence: 0.0, label: "NEUTRAL"}`
2. Tokeniza texto (max 512 tokens, padding, truncation)
3. Move tokens para device
4. Executa inference com `torch.no_grad()`
5. Aplica softmax aos logits
6. Mapeia classe para sentiment
7. Calcula confidence como `probabilities[predicted_id]`
8. Retorna resultado dict

**Tempo**: ~100-200ms (CPU), ~20-50ms (GPU)

**Exemplo**:

```python
# Inicialize antes
await engine.initialize()

# Analyze
result = await engine.analyze("Oi Mimi! Que dia maravilhoso!")

print(result["sentiment"])    # "happy"
print(result["confidence"])   # 0.96
print(result["label"])        # "POSITIVE"
print(result["logits"])       # [3.8, -1.2, 0.15]
```

**Caso de Uso - Tomada de Decisão**:

```python
result = await engine.analyze(user_message)

# Use confidence para ajustar comportamento
if result["confidence"] > 0.9:
    # Very confident - act on sentiment
    show_avatar_emotion(result["sentiment"])
elif result["confidence"] > 0.7:
    # Moderately confident - use with caution
    show_avatar_emotion(result["sentiment"])
else:
    # Low confidence - combine with other signals
    combined = combine_with_lexical(result)
    show_avatar_emotion(combined)
```

---

#### is_ready()

```python
def is_ready(self) -> bool
```

Verifica se engine está pronto para analyze.

**Retorno**: `bool`
- `True`: Modelo carregado e pronto
- `False`: Modelo não inicializado ou inicialização falhou

**Comportamento**: Retorna `self._initialized`

**Tempo**: ~1ns (instant)

**Exemplo**:

```python
if engine.is_ready():
    result = await engine.analyze(text)
else:
    result = fallback_lexical_analyze(text)
```

---

### SentimentBrain

```python
from agent.brains.sentiment_brain import SentimentBrain
```

#### Constructor (Atualizado)

```python
SentimentBrain(
    brain_id: str,
    event_bus,
    shared_state,
    sentiment_engine=None
) -> SentimentBrain
```

**Parâmetros**:

- `brain_id` (str): ID único para o brain
- `event_bus`: EventBus instance
- `shared_state`: SharedState instance
- `sentiment_engine` (Optional): BertSentimentEngine ou None
  - Default: `None`
  - Se None → usa fallback lexical
  - Se instance → usa BERT + fallback

**Exemplo**:

```python
# Sem engine (fallback sempre)
brain = SentimentBrain("sentiment", event_bus, shared_state)

# Com engine (BERT + fallback)
engine = BertSentimentEngine()
await engine.initialize()
brain = SentimentBrain("sentiment", event_bus, shared_state, sentiment_engine=engine)
```

---

#### _analyze_sentiment(text: str)

```python
def _analyze_sentiment(self, text: str) -> str
```

Análise de sentimento com fallback automático.

**Parâmetros**:

- `text` (str): Texto para análise

**Retorno**: `str` - "happy" | "sad" | "neutral"

**Lógica**:

```python
if engine exists AND engine.is_ready():
    try:
        result = await engine.analyze(text)
        return result["sentiment"]
    except Exception:
        log.warning("BERT failed, falling back")
        return fallback_lexical(text)
else:
    return fallback_lexical(text)
```

**Tempo**:
- Com BERT: 100-200ms
- Fallback: <1ms

**Exemplo**:

```python
sentiment = brain._analyze_sentiment("Que dia maravilhoso!")
# "happy" (via BERT)

sentiment = brain._analyze_sentiment("Que dia péssimo")
# "sad" (via BERT)

# Sem engine:
sentiment = brain._analyze_sentiment("Ok")
# "neutral" (via lexical fallback)
```

---

#### _analyze_sentiment_lexical(text: str)

```python
def _analyze_sentiment_lexical(self, text: str) -> str
```

Fallback: análise léxica simples.

**Parâmetros**:

- `text` (str): Texto para análise

**Retorno**: `str` - "happy" | "sad" | "neutral"

**Vocabulário**:

```python
positive_words = ["bom", "ótimo", "feliz", "adorar", "amar", "sim", "legal"]
negative_words = ["ruim", "péssimo", "triste", "odiar", "não", "nunca"]
```

**Lógica**:

1. Convert text to lowercase
2. Count occurrências de positive_words
3. Count occurrências de negative_words
4. Retorna resultado baseado em contagem maior

**Garantias**:
- Nunca fails
- Nunca exceção
- Sempre retorna string válida

**Tempo**: <1ms

**Exemplo**:

```python
sentiment = brain._analyze_sentiment_lexical("Ótimo dia!")
# "happy" (1 positive word)

sentiment = brain._analyze_sentiment_lexical("Péssimo!")
# "sad" (1 negative word)

sentiment = brain._analyze_sentiment_lexical("Ok")
# "neutral" (0 matches)
```

---

#### _detect_intent(text: str)

```python
def _detect_intent(self, text: str) -> str
```

Detecção de intenção (lexical, unchanged).

**Parâmetros**:

- `text` (str): Texto para análise

**Retorno**: `str` - um de 10 tipos:

```python
INTENT_PATTERNS = {
    "greeting": ["olá", "oi", "e aí", "como vai", "como está", "tudo bem", "opa"],
    "farewell": ["tchau", "adeus", "até logo", "até mais", "falou"],
    "gratitude": ["obrigada", "obrigado", "valeu", "muito obrigado"],
    "apology": ["desculpa", "desculpe", "me desculpe", "sorry"],
    "question": ["qual", "quando", "onde", "por quê", "como", "quanto", "quem"],
    "affirmation": ["sim", "claro", "com certeza", "tá bom", "ok"],
    "negation": ["não", "nunca", "jamais", "de jeito nenhum"],
    "request": ["pode", "poderia", "consegue", "dá pra", "tem como"],
    "complaint": ["problema", "ruim", "péssimo", "horrível", "não gosto"],
    "appreciation": ["legal", "ótimo", "adorei", "amei", "muito bom"],
}
```

**Tempo**: <1ms

**Exemplo**:

```python
intent = brain._detect_intent("Oi Mimi!")
# "greeting"

intent = brain._detect_intent("Qual é a data?")
# "question"

intent = brain._detect_intent("Tem algum problema")
# "complaint"
```

---

### AgentOrchestrator

```python
from agent.orchestrator import AgentOrchestrator
```

#### Constructor (Atualizado)

```python
AgentOrchestrator(
    user_id: str = "user_1",
    session_id: str | None = None,
    tts_provider: TTSProvider | None = None,
    llm_provider: LLMProvider | None = None,
    sentiment_engine=None
) -> AgentOrchestrator
```

**Parâmetros Novos**:

- `sentiment_engine` (Optional): BertSentimentEngine ou None
  - Default: `None`
  - Passado para SentimentBrain via dependency injection

**Exemplo**:

```python
engine = create_sentiment_engine()  # May be None

orchestrator = AgentOrchestrator(
    tts_provider=tts_provider,
    llm_provider=llm_provider,
    sentiment_engine=engine,
)
```

---

#### initialize()

```python
async def orchestrator.initialize() -> None
```

Inicializa todos os brains e components.

**Novo comportamento**:

1. Inicia shared_state
2. Inicia event_bus
3. **Inicia sentiment_engine (if exists)**
   - Chama `await sentiment_engine.initialize()`
   - Log: `"FinBERT-PT-BR model loaded successfully"`
   - Se falha: log warning, seta `sentiment_engine = None`
4. Inicia todos os 7 brains

**Exemplo**:

```python
orchestrator = AgentOrchestrator(sentiment_engine=engine)
await orchestrator.initialize()
# Model is now loaded and ready
```

---

## Funções Auxiliares

### create_sentiment_engine()

```python
from agent.main import create_sentiment_engine

def create_sentiment_engine() -> BertSentimentEngine | None
```

Provider factory function.

**Retorno**:

- `BertSentimentEngine`: Engine criado (não inicializado ainda)
- `None`: Se import falha ou erro ao criar

**Comportamento**:

1. Try import `BertSentimentEngine`
2. Create instance com `device="cpu"`
3. Return instance
4. Se qualquer erro → log warning, return None

**Tempo**: <1ms

**Exemplo**:

```python
engine = create_sentiment_engine()
if engine:
    await engine.initialize()
else:
    print("BERT not available, will use fallback")
```

---

## EventBus Integration

### Events Emitidos

#### SENTIMENT_UPDATED

Emitido por `SentimentBrain._on_user_text()`:

```python
{
    "type": "SENTIMENT_UPDATED",
    "payload": {
        "source": "user",
        "sentiment": "happy" | "sad" | "neutral",
        "intent": "greeting" | "question" | ... (10 types),
        "text": "original user text",
    }
}
```

#### EMOTION_DETECTED

Emitido por `SentimentBrain._on_agent_response()`:

```python
{
    "type": "EMOTION_DETECTED",
    "payload": {
        "source": "agent",
        "sentiment": "happy" | "sad" | "neutral",
        "text": "agent response text",
    }
}
```

---

## Error Handling

### Padrão Recomendado

```python
try:
    result = await engine.analyze(text)
except Exception as e:
    logger.warning(f"BERT analyze failed: {e}")
    result = fallback_lexical(text)
```

### Código Defensivo

```python
# SentimentBrain já implementa:
if self.sentiment_engine and self.sentiment_engine.is_ready():
    try:
        result = await self.sentiment_engine.analyze(text)
        return result.get("sentiment", "neutral")  # Safe dict access
    except Exception as e:
        logger.warning(f"BERT failed: {e}")  # Don't hide
        return self._analyze_sentiment_lexical(text)  # Fallback
else:
    return self._analyze_sentiment_lexical(text)  # Always works
```

---

## Exemplos Completos

### Exemplo 1: Análise Simples

```python
import asyncio
from agent.sentiment.bert_engine import BertSentimentEngine

async def main():
    engine = BertSentimentEngine(device="cpu")
    await engine.initialize()
    
    texts = [
        "Adorei!",
        "Que horror",
        "Tudo bem?",
    ]
    
    for text in texts:
        result = await engine.analyze(text)
        print(f"{text:20} → {result['sentiment']:8} ({result['confidence']:.2f})")

asyncio.run(main())
```

### Exemplo 2: Com Orchestrator

```python
import asyncio
from agent.orchestrator import AgentOrchestrator
from agent.main import create_sentiment_engine

async def main():
    engine = create_sentiment_engine()
    
    orchestrator = AgentOrchestrator(sentiment_engine=engine)
    await orchestrator.initialize()
    await orchestrator.start()
    
    # Sentiment analysis agora ativo
    # SentimentBrain usará BERT automaticamente

asyncio.run(main())
```

### Exemplo 3: Fallback Manual

```python
# Test both BERT e fallback
async def compare():
    engine = BertSentimentEngine()
    # Não inicializa - simula falha
    
    brain = SentimentBrain(
        "test",
        event_bus,
        shared_state,
        sentiment_engine=engine,  # Não pronto
    )
    
    # Usa lexical fallback
    result = brain._analyze_sentiment("Ótimo!")
    print(result)  # "happy" (via fallback)

asyncio.run(compare())
```

### Exemplo 4: Debugging

```python
# Check logits para entender decisão do modelo
result = await engine.analyze("Não é bom")

print(f"Text: 'Não é bom'")
print(f"Sentiment: {result['sentiment']}")
print(f"Confidence: {result['confidence']:.3f}")
print(f"Logits: {result['logits']}")
print(f"  POSITIVE: {result['logits'][0]:.2f}")
print(f"  NEGATIVE: {result['logits'][1]:.2f}")
print(f"  NEUTRAL:  {result['logits'][2]:.2f}")

# Output:
# Text: 'Não é bom'
# Sentiment: sad
# Confidence: 0.871
# Logits: [-0.45, 2.73, 0.21]
#   POSITIVE: -0.45
#   NEGATIVE:  2.73 ← highest
#   NEUTRAL:   0.21
```

---

## Troubleshooting Guide

### "BertSentimentEngine not available"

**Causa**: Import de transformers/torch falhou

**Fix**:
```bash
pip install torch transformers
```

### "Failed to load FinBERT-PT-BR model"

**Causa**: Arquivo não encontrado ou corrompido

**Fix**:
```bash
ls -l sentiment-model/
# Deve ter: pytorch_model.bin, config.json, tokenizer.json
```

### "is not a known attribute of None"

**Causa**: `model` ou `tokenizer` is None

**Fix**: Sempre chamar `await engine.initialize()` antes de `analyze()`

### Performance lenta (>200ms)

**Causa**: CPU-only (esperado)

**Fix**: Se disponível, use GPU:
```python
engine = BertSentimentEngine(device="cuda")
```

