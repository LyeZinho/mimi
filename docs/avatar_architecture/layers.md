# Camadas do Sistema

O sistema é dividido em três camadas principais, cada uma com responsabilidades bem definidas.

## 1. Camada IA (Python - Cérebro)

### Responsabilidades
- **Chatbot / LLM**: Processamento de linguagem natural, geração de respostas
- **Memória**: Armazenamento e recuperação de contexto conversacional
- **Análise de emoção**: Detecção de emoções no texto de entrada e saída
- **Decisão de gestos**: Seleção de animações apropriadas baseadas no contexto
- **Controle de estado**: Manutenção do estado emocional e comportamental do agente
- **Geração de voz**: Conversão de texto em fala (TTS)

### Exemplo de Estado do Agente
```json
{
  "emotion": "happy",
  "intent": "greeting",
  "gesture": "wave",
  "speech": "Olá! Que bom te ver aqui!",
  "timestamp": "2024-01-18T10:30:00Z"
}
```

## 2. Camada de Comunicação

Responsável pela transmissão de dados entre o cérebro e o corpo de forma eficiente e em tempo real.

### Protocolos Recomendados
1. **WebSocket** (Preferido)
   - Comunicação bidirecional
   - Conexão persistente
   - Ideal para aplicações em tempo real
   - Suporte nativo em Python e Unity

2. **OSC** (Open Sound Control)
   - Amplamente usado em VTubing
   - Baixa latência
   - Simples de implementar

3. **HTTP** (Não recomendado para real-time)
   - Polling frequente necessário
   - Maior overhead
   - Não adequado para sincronização precisa

## 3. Camada Unity (Avatar Engine - Corpo)

### Responsabilidades
- **Renderização 3D**: Exibição do avatar em tempo real
- **Animações**: Controle do Animator Controller
- **Expressões Faciais**: Manipulação de BlendShapes
- **Lip Sync**: Sincronização labial com áudio
- **Controle de Câmeras**: Posicionamento e movimento de câmeras
- **Servidor WebSocket**: Recepção de comandos do Python

Unity atua como um "servidor de avatar", recebendo comandos declarativos e executando as ações visuais correspondentes.