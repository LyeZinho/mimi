# 📚 Documentação Mimi

**Última Atualização:** 27 de Março de 2026 | **Status:** ✅ Estrutura documentada e verificada

---

## 🎯 Comece Aqui

### 📊 Visão Geral Completa
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** ← **COMECE AQUI** 📍
  - Estrutura completa de diretórios
  - 7 Brains autônomos explicados
  - Dependências e tecnologias
  - Fases de desenvolvimento
  - Fluxo de comunicação WebSocket

### 🚀 Início Rápido
- [QUICK_START.md](guides/QUICK_START.md) - Guia rápido para começar (3 terminais)
- [README.md](README.md) - Visão geral do projeto
- [STATUS.md](STATUS.md) - Status atual do sistema

---

## 🏗️ Arquitetura

### Documentação Principal
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Arquitetura detalhada dos 7 brains
- **[MULTI_BRAIN_GUIDE.md](MULTI_BRAIN_GUIDE.md)** - Guia completo do sistema multi-brain

### Detalhes por Camada
- [Visão Geral](avatar_architecture/overview.md)
- [Camadas](avatar_architecture/layers.md)
- [Melhores Práticas](avatar_architecture/best_practices.md)
- [Tecnologias](avatar_architecture/technologies.md)
- [Organização do Projeto](avatar_architecture/project_organization.md)

---

## 🧠 BERT Sentiment Analysis (NOVO!)

Integração de modelo FinBERT-PT-BR para análise de sentimento sofisticada.

### 📚 Documentação BERT
- **[BERT_DOCS_INDEX.md](BERT_DOCS_INDEX.md)** ← **COMECE AQUI** para BERT 📍
  - Mapa completo da documentação BERT
  - Guia "por onde começar" conforme seu cenário

### Guias Específicos
- **[BERT_SENTIMENT_INTEGRATION.md](BERT_SENTIMENT_INTEGRATION.md)** - Arquitetura e detalhes técnicos
- **[BERT_QUICKSTART.md](BERT_QUICKSTART.md)** - Teste e setup rápido
- **[BERT_API_REFERENCE.md](BERT_API_REFERENCE.md)** - Referência de API detalhada
- **[BERT_FAQ_MIGRATION.md](BERT_FAQ_MIGRATION.md)** - FAQ, troubleshooting e migration

### Resumo Rápido
- **Modelo**: FinBERT-PT-BR (1.4M textos financeiros portugueses)
- **Acurácia**: ~89% (vs ~70% keyword matching)
- **Latência**: 100-200ms (CPU), 20-50ms (GPU)
- **Status**: ✅ Produção
- **Fallback**: Automático para lexical se falha

---

## 🔊 TTS Voice Synthesis (NOVO!)

Integração de Piper TTS para síntese de voz offline com suporte a português.

### 📚 Documentação TTS
- **[TTS_IMPLEMENTATION.md](TTS_IMPLEMENTATION.md)** - Arquitetura, fix crítico e detalhes técnicos
- **[TTS_QUICKSTART.md](TTS_QUICKSTART.md)** - Teste, debug e guia rápido

### Resumo Rápido
- **Motor**: Piper TTS (pt_PT)
- **Tipo**: Offline-first, streaming
- **Latência**: 200-500ms (primeira parte), 1-5ms (chunks)
- **Status**: ✅ Fixo e testado (6/6 testes passando)
- **Bug Corrigido**: AsyncIterator handling em OutputBrain

---

## 📋 Planos & Implementação

### Phase 1: Enhanced Debug Panel (EM PLANEJAMENTO) 🔄
- **[2026-03-27-browser-control-debug-panel-design.md](plans/2026-03-27-browser-control-debug-panel-design.md)** - Design aprovado
- **[2026-03-27-browser-control-debug-panel-implementation.md](plans/2026-03-27-browser-control-debug-panel-implementation.md)** - Plano de implementação (20 tasks) ← **PRÓXIMA FASE**

### Phase 2-4: Browser Control (PLANEJAMENTO FUTURO)
- [Mirror & LLM Control Design](plans/2026-03-26-mirror-llm-control-design.md)
- [Ollama Setup](plans/2026-03-26-ollama-setup.md)
- [Development Plan](avatar_architecture/development_plan.md)

---

## 🔧 Guias de Setup

### Dev Setup
- [QUICK_START.md](guides/QUICK_START.md) - Começar em 3 terminais
- [Docker Dev Setup](guides/DOCKER_DEV_SETUP.md) - Setup com Docker
- [Fish Shell Setup](guides/FISH_SHELL_SETUP.md) - Configuração Fish Shell

### Integração
- [OBS Setup](guides/OBS_SETUP.md) - Streaming com OBS Studio

---

## 📖 Referência Técnica

### APIs & Protocolos
- [Mirror and Control](reference/MIRROR_AND_CONTROL.md) - WebSocket messages e controle
- [Sync Guide](reference/SYNC_GUIDE.md) - Sincronização avatar-áudio
- [Tools](reference/TOOLS.md) - Disponible tools registry
- [Walkthrough](reference/walkthrough.md) - Passo a passo completo

---

## 📊 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| **Código Python** | ~5.200 linhas |
| **Código React/JS** | ~2.800 linhas |
| **Documentação** | 15+ documentos |
| **Testes** | 30+ unitários |
| **Brains** | 7 autônomos |
| **Componentes React** | 10+ |

---

## 📝 Organização

- **[Project Info](project.md)** - Informações do projeto
- **[implementation-memo.md](implementation-memo.md)** - Memo de implementação

---

## 🔗 Links Rápidos

| Recurso | URL |
|---------|-----|
| **Web Interface** | http://localhost:5173 |
| **OBS Stream** | http://localhost:5173/obs.html |
| **Mirror Stream** | ws://localhost:8765 |

---

**Dica:** Se é primeira vez, leia [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) para entender todo o sistema. 📖
