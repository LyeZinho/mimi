# BERT Integration - FAQ & Migration Guide

## Perguntas Frequentes

### Funcionamento

#### P: Como funciona exatamente a análise BERT?

A: FinBERT-PT-BR é um modelo neural treinado em 1.4M textos financeiros portugueses. O fluxo é:

1. **Tokenização**: Texto → IDs numéricos (máx 512 tokens)
2. **Embedding**: IDs → vetores densos (contextualizados)
3. **Processamento**: Transformers (12 camadas BERT)
4. **Classificação**: 3 neurônios de saída (POSITIVE, NEGATIVE, NEUTRAL)
5. **Softmax**: Scores em probabilidades (0-1)
6. **Mapeamento**: POSITIVE→happy, NEGATIVE→sad, NEUTRAL→neutral

Diferença do keyword matching:
- Keyword: "bom" é sempre positivo
- BERT: "não é bom" → entende negação → classifica como negativo

#### P: Que tão confiável é o BERT comparado a keyword matching?

A: 

```
Métrica           | Keyword | BERT
----------------|---------|--------
Acurácia        | ~70%    | ~89%
Negação         | ✗       | ✓
Contexto        | ✗       | ✓
Ironia/Sarcasmo | ✗       | Parcial
Falsas positivas| Alto    | Médio
```

BERT é significativamente mais preciso, mas ainda tem limitações (ironia é difícil até para humanos).

#### P: O BERT funciona para outros idiomas além de português?

A: 

FinBERT-PT-BR foi treinado especificamente em português financeiro.

- ✅ Português: Excelente
- ⚠️ Português de outras regiões: Bom (mas pode ter diferenças)
- ❌ Outros idiomas: Não recomendado

Se quiser multilíngue, existem modelos como:
- `distilbert-base-multilingual-cased`
- `xlm-roberta-base`

Mas a performance será inferior ao FinBERT-PT-BR para português.

#### P: Quanto tempo leva a inicialização?

A:

```
Primeira vez (disk → RAM):  2-5 segundos
Inicializações subsequentes: ~0.5s (OS page cache)
Carregamento de cada texto:  100-200ms (CPU)
```

Isso é normal para modelos BERT. GPU seria ~20-50ms por texto.

#### P: E se o BERT falhar durante a análise?

A: Há 3 níveis de fallback automático:

```
1. Try BERT inference
   ↓ Success? Use result
   ↓ Exception? Log warning
   
2. Try lexical matching
   ↓ Success? Use result
   ↓ Exception? Never happens (safeguarded)
   
3. Return "neutral" (ultimate safe default)
```

O agent **nunca** crashes. Sempre funciona (degradado, mas funciona).

#### P: Posso desabilitar BERT e usar só keyword matching?

A: Sim! Duas formas:

```python
# Forma 1: Não passar engine
orchestrator = AgentOrchestrator(
    sentiment_engine=None
)

# Forma 2: Remover criar engine em main.py
sentiment_engine = None  # Skip create_sentiment_engine()
```

---

### Performance & Recursos

#### P: Quanto espaço em disco o modelo ocupa?

A:

```
pytorch_model.bin (pesos):    ~400 MB
config.json, tokenizer:       ~1-2 MB
Vocab.txt:                    ~1 MB
────────────────────────────
Total:                        ~402 MB
```

Já está no repositório (não precisa download).

#### P: Quanto RAM/VRAM é necessário?

A:

```
Carregamento do modelo:  ~500 MB
Runtime (activations):  ~100-200 MB
Safety margin:          ~100 MB
────────────────────────────
Total recomendado:      ~800 MB - 1 GB
```

**CPU**: Qualquer máquina moderna (até Raspberry Pi 4 funciona)
**GPU**: 1GB VRAM suficiente

#### P: Pode usar GPU?

A: Sim! Edite `agent/main.py`:

```python
def create_sentiment_engine():
    engine = BertSentimentEngine(device="cuda")  # ← GPU
    # ...
    return engine
```

**Speedup esperado**: ~5-10x mais rápido
- CPU: 100-200ms
- GPU: 20-30ms

Mas requer:
- NVIDIA GPU com CUDA
- `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`

#### P: Posso fazer batch inference (múltiplas frases ao mesmo tempo)?

A: Tecnicamente sim, mas não está implementado.

Atualmente:
```python
# Faz um de cada vez
for text in texts:
    result = await engine.analyze(text)  # Sequential
```

Para batch:
```python
# Seria assim (não implementado)
tokens_batch = tokenizer(texts, return_tensors="pt", padding=True)
outputs = model(**tokens_batch)
results = process_batch_outputs(outputs)
```

**Ganho**: ~2-3x mais rápido para 10 textos simultaneamente
**Implementação**: Futura se necessário (complexidade média)

---

### Integração & Deployment

#### P: Funciona em Docker?

A: Sim! ✅

```bash
docker-compose up
```

Logs esperados:
```
Loading FinBERT-PT-BR model from /app/sentiment-model/...
FinBERT-PT-BR model loaded successfully
```

Se não ver → check:
1. Arquivo `sentiment-model/pytorch_model.bin` existe?
2. Tem espaço em disco?
3. Permissões de leitura ok?

#### P: Funciona em produção?

A: Sim, mas com considerações:

```
✅ Model é determinístico (sempre mesma resposta para input)
✅ Não precisa conexão internet (offline-first)
✅ Fallback automático se falha
✅ Já em production em vários sistemas

⚠️ Lentidão em CPU (100-200ms por mensagem)
⚠️ Pode não generalizar bem para domínios fora de finança
⚠️ Nenhum A/B testing implementado ainda
```

Recomendação: 
- Monitorar métrica de fallback rate
- Se >5% → algo está errado
- Logar todas as predições para análise posterior

#### P: Como deploya em Kubernetes?

A: Padrão normal:

```yaml
# deployment.yaml
containers:
  - name: mimi-agent
    image: mimi:latest
    resources:
      requests:
        memory: "800Mi"
        cpu: "500m"
      limits:
        memory: "1Gi"
        cpu: "2000m"
    volumeMounts:
      - name: model-volume
        mountPath: /app/sentiment-model
volumes:
  - name: model-volume
    emptyDir: {}
```

**Importante**: 
- Montar `sentiment-model/` como volume (não duplicar)
- Pelo menos 1GB RAM por instância
- CPU não é crítico (model é IO-bound, não CPU-bound)

#### P: Preciso fazer versionamento do modelo?

A: Sim se:

1. Planejar fine-tuning futuro
2. Ter múltiplas versões A/B testing
3. Rastrear performance over time

Setup:

```
sentiment-model/
├── v1-original/
│   ├── pytorch_model.bin
│   ├── config.json
│   └── ...
├── v2-finetuned/
│   ├── pytorch_model.bin
│   └── ...
└── versions.json (metadados)
```

Depois atualizar `create_sentiment_engine()` para ler versão.

---

### Fine-tuning e Customização

#### P: Como fazer fine-tuning com dados próprios?

A: 3 passos:

1. **Coletar dados**:
   ```python
   # Log predictions que o modelo errou
   if prediction_wrong:
       save_to_training_set(text, correct_label)
   ```

2. **Preparar dataset**:
   ```python
   # Format: CSV com text, label
   # text,sentiment
   # "Que dia maravilhoso!",POSITIVE
   # "Horrível",NEGATIVE
   ```

3. **Fine-tune**:
   ```bash
   python -m torch.distributed.launch \
     --nproc_per_node 1 \
     train.py \
     --model_name_or_path bert-base-multilingual-cased \
     --train_file data/train.csv \
     --output_dir ./v2-finetuned/
   ```

Tempo: ~1-2 horas com 1000 exemplos e GPU

#### P: Posso adicionar mais classes (ex: "angry", "surprised")?

A: Sim! Mas requer:

1. Retraining do modelo (BertForSequenceClassification com N classes)
2. Novo dataset com os labels
3. Adequar mapeamento em `LABEL_MAP`

**Complexidade**: Média-alta
**Tempo**: 1-2 dias de trabalho

---

### Troubleshooting

#### P: Avatar sempre mostra emoção "neutral"

A: Causas possíveis:

1. **Engine não carregou**:
   ```bash
   grep "FinBERT-PT-BR model loaded" logs
   # Se não houver → model não carregou
   ```

2. **SentimentBrain não recebeu engine**:
   ```bash
   grep "sentiment_engine" agent/brains/sentiment_brain.py
   # Verificar se __init__ tem parameter
   ```

3. **Fallback ativo demais**:
   ```bash
   grep "BERT failed" logs | wc -l
   # Se número alto → investigar
   ```

**Fix**:
1. Restart agent
2. Check `sentiment-model/pytorch_model.bin` existe
3. Check permissões: `chmod 644 sentiment-model/pytorch_model.bin`

#### P: "CUDA out of memory"

A: Solução imediata:

```python
# Em agent/main.py
engine = BertSentimentEngine(device="cpu")  # ← Force CPU
```

Solução melhor:
- Usar GPU com mais VRAM (2GB+)
- Ou fazer quantization (INT8, meia-precisão)

#### P: Modelo carrega muito lentamente (>10s)

A: Causas:

1. **SSD lento**: Use CPU RAM disk
   ```bash
   # Linux
   mount -t tmpfs -o size=500m tmpfs /mnt/ramdisk
   cp sentiment-model/* /mnt/ramdisk/
   ```

2. **Network latency**: Se montado via NFS
   - Cache local do modelo
   - Ou copiar para local antes

3. **Primeiro carregamento é sempre lentho** (normal)

#### P: Predições inconsistentes / aleatórias

A: Isto NÃO deveria acontecer (BERT é determinístico).

Se estiver vendo:
1. **Check seed aleatória**:
   ```python
   import torch
   torch.manual_seed(42)
   ```

2. **Check diferentes versões de PyTorch**
   - Podem dar resultados levemente diferentes

3. **Check dropout ativo**:
   ```python
   # Em bert_engine.py
   self.model.eval()  # ← Já desativa dropout
   ```

---

## Migration Guide

### De Sistema Antigo (Keyword-only)

Se tinha:

```python
# Antigo
def _analyze_sentiment(text):
    for word in positive_words:
        if word in text.lower():
            return "happy"
    # ...
```

Para novo (BERT + fallback):

```python
# Novo
def _analyze_sentiment(self, text: str) -> str:
    if self.sentiment_engine and self.sentiment_engine.is_ready():
        try:
            result = await self.sentiment_engine.analyze(text)
            return result.get("sentiment", "neutral")
        except Exception as e:
            logger.warning(f"BERT failed: {e}")
            return self._analyze_sentiment_lexical(text)
    else:
        return self._analyze_sentiment_lexical(text)
```

**Passos**:

1. ✅ Já feito - código novo implementado
2. ✅ Já feito - fallback automático
3. ✅ Já feito - integração com orchestrator

Tudo pronto para usar!

### From Outro Sistema BERT

Se estava usando outro modelo BERT:

1. **Remova imports antigos**:
   ```python
   # Remove
   from other_bert import SentimentAnalyzer
   analyzer = SentimentAnalyzer("model-x")
   ```

2. **Use novo motor**:
   ```python
   from agent.sentiment.bert_engine import BertSentimentEngine
   engine = BertSentimentEngine()
   await engine.initialize()
   ```

3. **Resultado é compatível**:
   ```python
   # Antigo
   result = analyzer.analyze(text)  # Pode ser formato diferente
   
   # Novo
   result = await engine.analyze(text)
   # Sempre: {sentiment, confidence, label, logits}
   ```

---

## Checklist de Deployment

### Pré-Launch

- [ ] Modelo `sentiment-model/` existe em produção
- [ ] `pytorch_model.bin` integridade verificada
- [ ] Espaço em disco: mínimo 500MB livre
- [ ] RAM: mínimo 1GB disponível
- [ ] Python 3.10+, torch 2.0+, transformers 4.30+
- [ ] Testes passando: `pytest tests/test_bert_sentiment.py`
- [ ] Benchmarks rodados: `python benchmark_bert.py`
- [ ] Logs verificados: modelo carrega sem erros
- [ ] Fallback testado: remover engine, verificar lexical funciona

### Em Produção

- [ ] Monitorar `BertSentimentEngine initialized` em logs
- [ ] Monitorar taxa de fallback (`BERT failed` rate)
- [ ] Rastrear latência média de `analyze()`
- [ ] Coletar amostras de predições para análise
- [ ] Alertar se fallback rate > 5%
- [ ] Alertar se latência média > 500ms (indicador de problema)

### Maintenance

- [ ] Revisar dados coletados mensalmente
- [ ] Planejar fine-tuning se necessário
- [ ] Atualizar dependências trimestralmente
- [ ] A/B test novo modelo antes de colocar em produção

---

## Próximos Passos Recomendados

### Curto Prazo (1-2 semanas)

1. Testar em staging com dados reais
2. Monitorar accuracy vs keyword matching
3. Treinar suporte para lidar com feedback de usuários

### Médio Prazo (1-3 meses)

1. Coletar 500+ exemplos de conversas reais
2. Analisar erros do modelo
3. Planejar fine-tuning em domínio específico
4. Considerar GPU deployment se latência crítica

### Longo Prazo (3-6 meses)

1. Fine-tune com dados coletados
2. Implementar A/B testing
3. Adicionar mais classes (ex: anger, surprise)
4. Multilingual support se necessário

---

## Ressources Adicionais

### Documentação
- [BERT_SENTIMENT_INTEGRATION.md](BERT_SENTIMENT_INTEGRATION.md) - Arquitetura completa
- [BERT_QUICKSTART.md](BERT_QUICKSTART.md) - Teste e setup
- [BERT_API_REFERENCE.md](BERT_API_REFERENCE.md) - API detalhada

### Código
- `agent/sentiment/bert_engine.py` - Implementação
- `agent/brains/sentiment_brain.py` - Integração
- `tests/test_bert_sentiment.py` - Testes

### Papers
- [FinBERT](https://arxiv.org/abs/1910.03046)
- [BERT Original](https://arxiv.org/abs/1810.04805)

### Comunidades
- [HuggingFace Forums](https://discuss.huggingface.co/)
- [PyTorch Forums](https://discuss.pytorch.org/)
- Stack Overflow (tag: `bert`, `transformers`, `sentiment-analysis`)

