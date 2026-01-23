# OBS Streaming Setup Guide

## 🎥 Como usar o Avatar no OBS

### Opção 1: Chroma Key (Fundo Verde)

1. **Inicie o servidor**:
   ```bash
   python start.py
   ```

2. **No OBS**:
   - Adicione uma fonte → **Browser**
   - URL: `http://localhost:8000/obs.html`
   - Largura: 1920
   - Altura: 1080
   - ✅ Marque "Shutdown source when not visible"

3. **Adicione Filtro de Chroma Key**:
   - Clique com botão direito na fonte → **Filtros**
   - Adicione **Chroma Key**
   - Tipo de Chave: Verde
   - Similaridade: 400
   - Suavidade: 80

### Opção 2: Fundo Transparente

Use a URL com parâmetro de cor:
```
http://localhost:8000/obs.html?bg=000000
```

Cores disponíveis:
- `00ff00` - Verde (chroma key)
- `000000` - Preto
- `0000ff` - Azul
- `ff00ff` - Magenta

### Opção 3: Modelo Diferente

```
http://localhost:8000/obs.html?model=Mimi01.vrm
```

### Combinando Parâmetros

```
http://localhost:8000/obs.html?model=Mimi01.vrm&bg=00ff00&controls=false
```

Parâmetros disponíveis:
- `model` - Nome do arquivo VRM (ex: `Mimi.vrm`)
- `bg` - Cor de fundo em hexadecimal (ex: `00ff00`)
- `controls` - Habilitar controles de câmera (`true`/`false`)

## 🎮 Controlando o Avatar

O avatar responde automaticamente aos comandos do WebSocket.

### Via Python

```python
from agent.avatar import WebAvatar

avatar = WebAvatar()
await avatar.connect()

# Mudar expressão
await avatar.set_expression('happy')

# Falar
await avatar.speak_start()
await asyncio.sleep(2)
await avatar.speak_end()
```

### Via Demo

```bash
python web_avatar/demo_web_avatar.py
```

## 🔧 Troubleshooting

### Avatar não aparece no OBS

1. Verifique se o servidor está rodando (`python start.py`)
2. Teste a URL no navegador primeiro
3. Verifique se a porta 8000 está acessível

### Expressões não mudam

1. Verifique se o WebSocket está conectado (canto superior direito)
2. Veja os logs do servidor
3. Teste com `demo_web_avatar.py`

### Performance ruim

1. Reduza a resolução no OBS (1280x720)
2. Desabilite antialiasing
3. Use um modelo VRM mais leve

## 💡 Dicas

- **Posicionamento**: Ajuste a câmera editando `obs.html` (linha `camera.position.set(0, 1.4, 2)`)
- **Iluminação**: Modifique as luzes no código para melhor resultado
- **Qualidade**: Use resolução 1920x1080 para melhor qualidade
- **FPS**: O avatar roda a 60 FPS por padrão

## 📊 Configurações Recomendadas OBS

- **Resolução**: 1920x1080 ou 1280x720
- **FPS**: 30 ou 60
- **Chroma Key Similarity**: 400
- **Chroma Key Smoothness**: 80
- **Shutdown when not visible**: ✅ Ativado (economiza recursos)
