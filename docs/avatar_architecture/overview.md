# Visão Geral da Arquitetura

A arquitetura proposta separa claramente as responsabilidades entre o "cérebro" (Python) e o "corpo" (Unity), permitindo um sistema modular e escalável para agentes IA com avatares 3D.

## Diagrama Conceitual

```
┌──────────────────────────────┐
│        PYTHON (CÉREBRO)       │
│  - IA / LLM                  │
│  - Emoções                   │
│  - Diálogo                   │
│  - TTS                       │
│  - Estado do agente          │
└──────────────┬───────────────┘
               │ (WebSocket / OSC)
┌──────────────▼───────────────┐
│        UNITY (CORPO)          │
│  - Render 3D                 │
│  - Animações                 │
│  - Expressões (BlendShapes)  │
│  - Lip Sync                  │
│  - Câmeras                   │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│        OBS / STREAM           │
│  - Captura                   │
│  - Cena                      │
│  - Transmissão               │
└──────────────────────────────┘
```

## Princípios Fundamentais

- **Python nunca renderiza**: Responsável apenas pela lógica de IA, processamento de linguagem e geração de comandos.
- **Unity nunca "pensa"**: Focado exclusivamente na apresentação visual e animações, recebendo comandos declarativos.
- **Comunicação clara e desacoplada**: Uso de protocolos como WebSocket para comunicação bidirecional em tempo real.

Esta separação permite:
- Troca fácil de componentes (IA, voz, avatar)
- Desenvolvimento paralelo das equipes
- Escalabilidade para múltiplos avatares
- Integração com sistemas de streaming