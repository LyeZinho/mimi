# Web Avatar Quick Start Guide

## 🚀 Início Rápido

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar Sistema
```bash
python web_avatar/start_web_avatar.py
```

### 3. Abrir Navegador
Acesse: **http://localhost:8000**

### 4. Carregar Modelo
- Selecione "Mimi.vrm" no dropdown
- Ou arraste um arquivo .vrm para a página

### 5. Testar Expressões
Clique nos botões de expressão:
- 😐 Neutro
- 😊 Feliz
- 😢 Triste
- 😠 Bravo
- 😲 Surpreso
- 😌 Relaxado

## 🔌 Integração com Agente

### Configurar
```bash
echo "AVATAR_TYPE=web" > .env
```

### Usar no Código
```python
from agent.avatar import WebAvatar

avatar = WebAvatar()
await avatar.connect()
await avatar.set_expression('happy')
```

## 🎮 Controles

### Mouse
- **Arrastar**: Rotacionar câmera
- **Scroll**: Zoom in/out
- **Botão direito**: Pan

### Botões
- **Piscar**: Animar piscada
- **Falar**: Simular fala (lip-sync)
- **Resetar**: Voltar posição inicial

## ⚙️ Configurações

### Portas Padrão
- HTTP: `8000`
- WebSocket: `8765`

### Alterar Portas
```bash
# .env
WEB_AVATAR_PORT=9000
WEBSOCKET_PORT=9001
```

## 🐛 Troubleshooting

### Modelo não carrega
- Verifique se o arquivo .vrm está em `vroid_model/`
- Veja o console do navegador (F12) para erros

### WebSocket não conecta
- Certifique-se que `start_web_avatar.py` está rodando
- Verifique se a porta 8765 está livre

### Página em branco
- Limpe o cache do navegador
- Verifique se o servidor HTTP está rodando na porta 8000

## 📚 Recursos

- **Documentação completa**: [README.md](file:///e:/git/Mimi/README.md)
- **Walkthrough**: [walkthrough.md](file:///C:/Users/pedro/.gemini/antigravity/brain/70bc465b-8ab4-434b-b2c0-fbc5d0248382/walkthrough.md)
- **Three.js**: https://threejs.org/
- **three-vrm**: https://github.com/pixiv/three-vrm

## 🎯 Próximos Passos

1. ✅ Testar com seus próprios modelos VRM
2. ✅ Integrar com o agente Mimi
3. ✅ Customizar expressões e animações
4. ✅ Adicionar novos gestos
5. ✅ Experimentar com iluminação e cenário
