# Tecnologias Necessárias

## Unity (Corpo do Avatar)

### Versão Recomendada
- Unity 2021 LTS ou superior
- Suporte a URP (Universal Render Pipeline) para melhor performance

### Pacotes Essenciais
- **UniVRM**: Para carregamento e manipulação de modelos VRM
  - Importação de avatares VRM
  - Controle de BlendShapes
  - Configuração de humanoid

- **WebSocket Server**: Biblioteca C# para comunicação
  - `WebSocketSharp` ou `NativeWebSocket`
  - Implementação do servidor WebSocket

### Componentes Unity
- **Animator Controller**: Para controle de animações
- **VRM BlendShape Proxy**: Para expressões faciais
- **Audio Source**: Para reprodução de voz
- **Camera Controller**: Para controle de câmeras

## Python (Cérebro IA)

### Bibliotecas Core
- **websockets**: Para comunicação WebSocket
- **fastapi**: Framework web com suporte a WebSocket (opcional)
- **asyncio**: Para operações assíncronas

### IA e Linguagem
- **openai**: Cliente para API OpenAI GPT
- **transformers**: Para modelos locais (Hugging Face)
- **langchain**: Framework para construção de agentes IA

### Voz (TTS)
- **coqui-tts**: TTS open-source de alta qualidade
- **elevenlabs**: API comercial de voz
- **azure-cognitiveservices-speech**: TTS da Microsoft

### Outros
- **pydantic**: Para validação de dados e modelos
- **loguru**: Para logging estruturado
- **python-dotenv**: Para configuração de ambiente

## Infraestrutura

### Streaming
- **OBS Studio**: Para captura e transmissão
- **Virtual Camera**: Para integração com Unity

### Desenvolvimento
- **Git**: Controle de versão
- **Docker**: Containerização (opcional)
- **VS Code**: IDE com extensões Python e C#

## Hardware Recomendado

### Desenvolvimento
- CPU: Intel i5 ou AMD Ryzen 5
- RAM: 16GB mínimo
- GPU: GTX 1060 ou equivalente (para Unity)

### Produção/Streaming
- CPU: Intel i7 ou AMD Ryzen 7
- RAM: 32GB
- GPU: RTX 3060 ou superior
- Webcam HD para captura adicional