# Quick Start: BERT Sentiment Analysis

## Testando Localmente (Sem Docker)

### 1. Setup

```bash
# Navegue ao repositório
cd /home/pedro/repo/mimi

# Ative venv
source .venv/bin/activate

# Instale dependências (se necessário)
pip install torch transformers

# Verifique se o modelo existe
ls -lh sentiment-model/
# pytorch_model.bin       ~400M
# config.json
# tokenizer.json
# vocab.txt
```

### 2. Teste Manual (Script Rápido)

Crie `test_bert_quick.py`:

```python
#!/usr/bin/env python3
"""Quick test for BertSentimentEngine."""

import asyncio
from pathlib import Path

# Add repo to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from agent.sentiment.bert_engine import BertSentimentEngine


async def test_bert():
    """Test BERT sentiment analysis."""
    
    # Create and initialize engine
    print("[1] Initializing engine...")
    engine = BertSentimentEngine(device="cpu")
    await engine.initialize()
    print("✓ Engine initialized\n")
    
    # Test cases
    test_cases = [
        ("Oi Mimi! Que dia maravilhoso! Adorei tudo!", "happy"),
        ("Que dia péssimo, nada funcionou", "sad"),
        ("Qual é a data de hoje?", "neutral"),
        ("Não é bom, tudo está ruim", "sad"),  # Negation test
        ("Sim, tudo ótimo!", "happy"),
    ]
    
    print("[2] Testing inference...\n")
    for text, expected in test_cases:
        result = await engine.analyze(text)
        sentiment = result["sentiment"]
        confidence = result["confidence"]
        label = result["label"]
        
        match = "✓" if sentiment == expected else "✗"
        print(f"{match} Input: '{text}'")
        print(f"  → Sentiment: {sentiment} (confidence: {confidence:.2f})")
        print(f"  → Label: {label}")
        print(f"  → Logits: {[f'{x:.2f}' for x in result['logits']]}")
        print()


if __name__ == "__main__":
    asyncio.run(test_bert())
```

Rodando:

```bash
python test_bert_quick.py
```

**Saída esperada**:

```
[1] Initializing engine...
Loading FinBERT-PT-BR model from /home/pedro/repo/mimi/sentiment-model/...
FinBERT-PT-BR model loaded successfully
✓ Engine initialized

[2] Testing inference...

✓ Input: 'Oi Mimi! Que dia maravilhoso! Adorei tudo!'
  → Sentiment: happy (confidence: 0.96)
  → Label: POSITIVE
  → Logits: [3.82, -1.23, 0.15]

✓ Input: 'Que dia péssimo, nada funcionou'
  → Sentiment: sad (confidence: 0.88)
  → Label: NEGATIVE
  → Logits: [-0.52, 2.91, 0.08]

✓ Input: 'Qual é a data de hoje?'
  → Sentiment: neutral (confidence: 0.85)
  → Label: NEUTRAL
  → Logits: [0.34, -0.18, 2.14]

✓ Input: 'Não é bom, tudo está ruim'
  → Sentiment: sad (confidence: 0.87)
  → Label: NEGATIVE
  → Logits: [-0.45, 2.73, 0.21]

✓ Input: 'Sim, tudo ótimo!'
  → Sentiment: happy (confidence: 0.94)
  → Label: POSITIVE
  → Logits: [3.51, -1.35, 0.09]
```

---

## Testando com Docker

### 1. Build e Run

```bash
cd /home/pedro/repo/mimi

# Build
docker-compose build

# Run
docker-compose up
```

### 2. Watch Logs (Em outro terminal)

```bash
docker-compose logs -f agent
```

**Procure por**:

```
BertSentimentEngine created
Loading FinBERT-PT-BR model
FinBERT-PT-BR model loaded successfully
BertSentimentEngine initialized
```

Se ver isso tudo → ✓ BERT carregou com sucesso

### 3. Teste com Chat

Abra http://localhost:5173 e converse:

1. **Frase positiva**: "Oi Mimi! Tudo bem?"
   - Avatar deve mostrar expressão happy 😊
   - Log deve mostrar: `sentiment: happy`

2. **Frase negativa**: "Que dia horrível, nada funciona"
   - Avatar deve mostrar expressão sad 😢
   - Log deve mostrar: `sentiment: sad`

3. **Frase neutra**: "Qual é o significado de vida?"
   - Avatar deve mostrar expressão neutra 😐
   - Log deve mostrar: `sentiment: neutral`

---

## Monitorando Performance

### 1. Timing da Inicialização

```bash
docker-compose logs agent | grep -E "(Loading|loaded|initialized)"
```

**Esperado**:
```
t=0s   | BertSentimentEngine created
t=0.5s | Loading FinBERT-PT-BR model...
t=2.3s | FinBERT-PT-BR model loaded successfully
t=2.3s | BertSentimentEngine initialized
```

### 2. Latência por Mensagem

```bash
docker-compose logs agent | grep -E "analyze|sentiment"
```

**Esperado**: ~100-200ms por `analyze()` call em CPU

### 3. Taxa de Fallback

```bash
docker-compose logs agent | grep "BERT failed"
```

**Esperado em produção**: 0 (engine deve estar pronto)

### 4. Uso de Memória

```bash
docker stats --no-stream agent
```

**Esperado**:
- MEMORY: ~600-800MB (model + runtime)
- CPU: ~0% idle, ~100% durante inference

---

## Testes Unitários

### Criar `tests/test_bert_sentiment.py`

```python
"""Unit tests for BertSentimentEngine."""

import pytest
import asyncio
from agent.sentiment.bert_engine import BertSentimentEngine


@pytest.fixture
async def engine():
    """Create and initialize engine for tests."""
    engine = BertSentimentEngine(device="cpu")
    await engine.initialize()
    yield engine


@pytest.mark.asyncio
async def test_initialization(engine):
    """Test engine initializes correctly."""
    assert engine.is_ready()
    assert engine.model is not None
    assert engine.tokenizer is not None


@pytest.mark.asyncio
async def test_positive_sentiment(engine):
    """Test positive sentiment detection."""
    result = await engine.analyze("Que dia maravilhoso!")
    assert result["sentiment"] == "happy"
    assert result["confidence"] > 0.8
    assert result["label"] == "POSITIVE"


@pytest.mark.asyncio
async def test_negative_sentiment(engine):
    """Test negative sentiment detection."""
    result = await engine.analyze("Que dia péssimo, nada funciona")
    assert result["sentiment"] == "sad"
    assert result["confidence"] > 0.8
    assert result["label"] == "NEGATIVE"


@pytest.mark.asyncio
async def test_neutral_sentiment(engine):
    """Test neutral sentiment detection."""
    result = await engine.analyze("Qual é a data de hoje?")
    assert result["sentiment"] == "neutral"
    assert result["confidence"] > 0.7
    assert result["label"] == "NEUTRAL"


@pytest.mark.asyncio
async def test_negation_handling(engine):
    """Test that negation is properly handled."""
    # "Não é bom" should be negative
    result = await engine.analyze("Não é bom")
    assert result["sentiment"] == "sad"


@pytest.mark.asyncio
async def test_confidence_scores(engine):
    """Test that confidence scores are valid."""
    result = await engine.analyze("Adorei!")
    assert 0 <= result["confidence"] <= 1.0
    assert len(result["logits"]) == 3


@pytest.mark.asyncio
async def test_long_text_truncation(engine):
    """Test that long texts are properly truncated."""
    long_text = "Ótimo! " * 200  # >512 tokens
    result = await engine.analyze(long_text)
    assert result["sentiment"] in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
async def test_empty_text(engine):
    """Test handling of empty text."""
    result = await engine.analyze("")
    assert result["sentiment"] in ["happy", "sad", "neutral"]


@pytest.mark.asyncio
async def test_uninitialized_engine():
    """Test that uninitialized engine returns safe default."""
    engine = BertSentimentEngine(device="cpu")  # Don't initialize
    result = await engine.analyze("Teste")
    assert result["sentiment"] == "neutral"
    assert result["confidence"] == 0.0
```

Rodando testes:

```bash
pytest tests/test_bert_sentiment.py -v --asyncio-mode=auto
```

---

## Benchmarking

### Script: `benchmark_bert.py`

```python
#!/usr/bin/env python3
"""Benchmark BERT sentiment engine."""

import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from agent.sentiment.bert_engine import BertSentimentEngine


async def benchmark():
    """Run performance benchmarks."""
    
    engine = BertSentimentEngine(device="cpu")
    
    # Benchmark initialization
    print("[Initialization Benchmark]")
    t0 = time.time()
    await engine.initialize()
    init_time = time.time() - t0
    print(f"  Model load: {init_time:.2f}s")
    
    # Benchmark inference
    print("\n[Inference Benchmark]")
    test_texts = [
        "Oi Mimi, tudo bem?",
        "Que dia maravilhoso!",
        "Não é bom, tudo está ruim",
        "Qual é a data de hoje?",
        "Adorei demais, sensacional!",
    ]
    
    times = []
    for text in test_texts:
        t0 = time.time()
        result = await engine.analyze(text)
        elapsed = time.time() - t0
        times.append(elapsed)
        print(f"  '{text[:30]}...' → {result['sentiment']:<7} ({elapsed*1000:.1f}ms)")
    
    # Summary
    print(f"\n[Summary]")
    print(f"  Min latency: {min(times)*1000:.1f}ms")
    print(f"  Max latency: {max(times)*1000:.1f}ms")
    print(f"  Avg latency: {sum(times)/len(times)*1000:.1f}ms")
    print(f"  Throughput: {1/sum(times)*len(times):.1f} req/sec")


if __name__ == "__main__":
    asyncio.run(benchmark())
```

Rodando:

```bash
python benchmark_bert.py
```

**Saída esperada**:

```
[Initialization Benchmark]
  Model load: 3.45s

[Inference Benchmark]
  'Oi Mimi, tudo bem?' → happy (142ms)
  'Que dia maravilhoso!' → happy (135ms)
  'Não é bom, tudo está ruim' → sad (138ms)
  'Qual é a data de hoje?' → neutral (140ms)
  'Adorei demais, sensacional!' → happy (137ms)

[Summary]
  Min latency: 135.2ms
  Max latency: 142.1ms
  Avg latency: 138.6ms
  Throughput: 7.2 req/sec
```

---

## Testando Fallback

### Script: `test_fallback.py`

```python
#!/usr/bin/env python3
"""Test fallback to lexical analysis."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.brains.sentiment_brain import SentimentBrain
from agent.core.messaging import get_event_bus, get_shared_state


async def test_fallback():
    """Test that fallback works when engine unavailable."""
    
    event_bus = get_event_bus()
    shared_state = get_shared_state()
    await event_bus.start()
    
    # Create SentimentBrain WITHOUT engine (None)
    print("[Fallback Test] Initializing SentimentBrain without engine...")
    brain = SentimentBrain("test_brain", event_bus, shared_state, sentiment_engine=None)
    await brain.initialize()
    print("✓ Brain initialized\n")
    
    # Test lexical fallback
    test_cases = [
        ("Ótimo!", "happy"),
        ("Péssimo", "sad"),
        ("Ok", "neutral"),
    ]
    
    print("[Testing Fallback Sentiment Analysis]")
    for text, expected in test_cases:
        result = brain._analyze_sentiment(text)
        match = "✓" if result == expected else "✗"
        print(f"{match} '{text}' → {result} (expected: {expected})")


if __name__ == "__main__":
    asyncio.run(test_fallback())
```

Rodando:

```bash
python test_fallback.py
```

**Saída esperada**:

```
[Fallback Test] Initializing SentimentBrain without engine...
✓ Brain initialized

[Testing Fallback Sentiment Analysis]
✓ 'Ótimo!' → happy (expected: happy)
✓ 'Péssimo' → sad (expected: sad)
✓ 'Ok' → neutral (expected: neutral)
```

---

## CI/CD Integration

### GitHub Actions (`.github/workflows/test-bert.yml`)

```yaml
name: Test BERT Sentiment

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio
      
      - name: Run BERT tests
        run: pytest tests/test_bert_sentiment.py -v --asyncio-mode=auto
      
      - name: Run benchmark
        run: python benchmark_bert.py
```

---

## Debugging Avançado

### 1. Habilitar Debug Logging

Edite `agent/sentiment/bert_engine.py`:

```python
import logging

# Set to DEBUG for verbose output
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

### 2. Inspect Model Outputs

```python
# Print raw logits before softmax
async def analyze_debug(self, text: str):
    tokens = self.tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
    outputs = self.model(**tokens)
    
    logits = outputs.logits[0]
    print(f"Raw logits: {logits}")
    
    probs = torch.softmax(logits, dim=0)
    print(f"Probabilities: {probs}")
    
    # This helps understand model confidence
```

### 3. Tokenizer Inspection

```python
# Check how text is tokenized
tokens = engine.tokenizer.encode("Não é bom", return_tensors="pt")
print(f"Token IDs: {tokens}")

decoded = engine.tokenizer.decode(tokens[0])
print(f"Decoded: {decoded}")

# This helps debug edge cases
```

---

## Próximos Passos

1. ✅ BERT integrado
2. ✅ Fallback automático
3. ✅ Testes criados
4. ⬜ Monitorar métricas em produção
5. ⬜ Coletar dados para fine-tuning
6. ⬜ GPU support

