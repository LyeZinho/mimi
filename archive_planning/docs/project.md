Agente de IA Interativo Multimodal — Versão aprimorada

1. Elevator Pitch

Agente multimodal leve e offline-first que combina reconhecimento de voz, LLM local e TTS para criar interfaces conversacionais reativas e acionáveis — escalável para avatar 3D e integrações externas.

2. Problema

Interfaces atuais de voz/assistentes são geralmente fragmentadas, dependem fortemente de nuvem e não permitem fácil extensibilidade para automações e controle de estado interno persistente.

3. Solução proposta

Construir um agente cognitivo modular que:
- Rode preferencialmente localmente (offline-first);
- Trate voz e texto de forma unificada;
- Separe raciocínio (LLM) da execução (actions/router);
- Exporte intenções estruturadas que orquestram TTS, estados e integrações externas.

4. Público-alvo

- Desenvolvedores de aplicações multimodais (VR, robótica, assistentes pessoais);
- Criadores de conteúdo com avatar/VTuber;
- Projetos embarcados ou de privacidade que exigem processamento local.

5. Proposta de Valor e Diferenciais

- Privacidade e latência reduzida por execução local;
- Arquitetura modular que facilita substituir modelos (STT/LLM/TTS);
- Foco em intenções estruturadas para automação segura;
- Preparado para expansão multimodal (3D, visão) sem reescrita.

6. Features Principais (Resumido)

- STT local com VAD (voz contínua de baixa latência);
- Input Manager (unifica voz/texto);
- Agent Core com estado explícito e memória;
- LLM Core (inference local) com saída estruturada (intents);
- Action Router para TTS, mudanças de estado e chamadas externas;
- TTS local com suporte a emoções e marcadores de tempo;
- Subsystem para conectar avatar 3D via WebSocket/OSC.

7. MVP (mínimo viável)

- Captura de áudio com VAD → STT (faster-whisper/whisper.cpp);
- Input Manager + Agent Core básico;
- LLM local (Mistral/Qwen via llama.cpp/Ollama) para intents;
- Action Router com TTS (Piper/Coqui) e resposta textual;
- UI simples (terminal ou web) para testar conversas.

8. Backlog inicial (primeiras tarefas)

1. Infra: projeto e estrutura de pastas (esqueleto do repo).
2. Implementar Input Manager e pipeline de áudio (microfone→VAD→STT).
3. Integrar LLM local e criar prompt templates para intents.
4. Action Router básico (speak, text_reply, set_state).
5. Integrar TTS local e sincronizar markers de fala.
6. Sistema de memória curto-prazo (deque) e persistente (sqlite).
7. Testes end-to-end do fluxo voz→intenção→resposta.
8. Documentação e exemplos de uso (README e demo).

9. Arquitetura técnica (alto-nível)

- Input: Microfone / Texto → VAD / Text Input
- Input Manager: normalização, metadados, enfileiramento
- Agent Core: estado, políticas simples, gating para chamada ao LLM
- LLM Core: gera intenção estruturada (JSON)
- Action Router: mapeia intent → executores (TTS, state, webhook)
- Output: TTS / text / eventos para avatar

10. Stack recomendado

- STT: faster-whisper / whisper.cpp
- LLM: Mistral 7B Instruct / Qwen 2.5 (rodando via llama.cpp ou Ollama)
- TTS: Piper TTS (leve) ou Coqui para síntese mais expressiva
- Orquestração: Python (asyncio), pydantic para schemas, sqlite para persistência
- Voz/áudio: sounddevice, webrtcvad

11. Requisitos não-funcionais

- Offline-first com opção de fallback para serviços remotos;
- Latência de resposta de voz < 300–500 ms para STT+LLM+TTS (meta dependente do hardware);
- Modularidade: componentes substituíveis via interfaces bem definidas;
- Observabilidade mínima: logs e métricas para latência e acurácia.

12. Métricas de sucesso

- Latência média do fluxo (STT→LLM→TTS);
- Taxa de intenção correta (avaliada manualmente em amostra);
- Uso de CPU/RAM em hardware-alvo;
- Retenção de contexto por sessão (memória útil).

13. Riscos e mitigação

- Risco: modelos locais exigem hardware potente. Mitigação: oferecer quantização, modelos menores e modo cloud-fallback.
- Risco: falhas na detecção de intenções. Mitigação: validação de intents, confirmação ao usuário antes de ações sensíveis.
- Risco: latência alta em TTS. Mitigação: pré-renderização de frases comuns e TTS streaming.

14. Roadmap de alto nível

- Fase 1 (0–2 meses): MVP local voz+texto, LLM básico, TTS e demo.
- Fase 2 (2–5 meses): Memória persistente, intents avançadas, ferramentas externas.
- Fase 3 (5–9 meses): Integração avatar 3D, visão multimodal, deploy em edge devices.

15. Próximos passos imediatos

- Validar público e casos de uso prioritários (3 entrevistas rápidas);
- Montar repositório com esqueleto e CI simples;
- Implementar prova de conceito STT→LLM→TTS em um script.

16. Conclusão

Esta versão foca em transformar a arquitetura técnica já escrita em um produto mínimo viável com proposição de valor clara: privacidade, baixa latência e modularidade para evolução multimodal. Posso aplicar esse texto diretamente em `project.md` e criar o esqueleto inicial do repositório — quer que eu atualize o arquivo agora?