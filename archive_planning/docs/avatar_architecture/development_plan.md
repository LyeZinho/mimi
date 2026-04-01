# Plano de Desenvolvimento (Passo a Passo)

## Fase 1 — Base do Avatar (Unity)

### 1. Configuração do Projeto Unity
- Criar novo projeto 3D com URP
- Instalar UniVRM via Package Manager
- Configurar render pipeline para VRoid

### 2. Importação de Modelos VRM
- Importar arquivos .vrm para Assets
- Verificar configuração Humanoid:
  - Bone mapping correto
  - T-pose adequada
- Verificar BlendShapes:
  - Expressões nomeadas (Joy, Angry, Sad, etc.)
  - BlendShapes funcionais

### 3. Animator Controller Básico
Criar estados:
- **Idle**: Estado padrão, loop contínuo
- **Talk**: Animação de fala
- **Gesture_Wave**: Aceno
- **Gesture_Think**: Pensativo
- **Gesture_Point**: Apontar

Usar Triggers para transições:
- `Wave`, `Think`, `Talk`, `Point`

## Fase 2 — Controle de Expressões

### ExpressionController.cs
```csharp
using UnityEngine;
using VRM;

public class ExpressionController : MonoBehaviour
{
    [SerializeField] private VRMBlendShapeProxy vrmBlendShapeProxy;

    public void SetExpression(string name, float value)
    {
        vrmBlendShapeProxy.ImmediatelySetValue(
            BlendShapeKey.CreateFromPreset(name),
            value
        );
    }

    public void ResetExpressions()
    {
        // Reset all expressions to neutral
        vrmBlendShapeProxy.ImmediatelySetValue(BlendShapeKey.CreateFromPreset("Neutral"), 1f);
    }
}
```

### Expressões Recomendadas
- Neutral (padrão)
- Happy/Joy
- Sad
- Angry
- Surprised
- Blink (piscar)

## Fase 3 — Lip Sync

### Opção Simples (Volume-based)
- Analisar amplitude do áudio
- Mapear para abertura da boca
- BlendShape "A" ou "O" baseado no volume

### Opção Profissional
- **OVRLipSync**: Análise de fonemas
- **Rhubarb Lip Sync**: Baseado em timing
- Visemes manuais para controle preciso

### Implementação Básica
```csharp
public class LipSyncController : MonoBehaviour
{
    [SerializeField] private AudioSource audioSource;
    [SerializeField] private ExpressionController expressionController;

    void Update()
    {
        float volume = GetAudioVolume();
        expressionController.SetExpression("A", volume);
    }

    private float GetAudioVolume()
    {
        // Implementar análise de volume
        return 0f;
    }
}
```

## Fase 4 — Servidor WebSocket no Unity

### WebSocketServer.cs
```csharp
using WebSocketSharp.Server;

public class WebSocketServer : MonoBehaviour
{
    private WebSocketServer wss;

    void Start()
    {
        wss = new WebSocketServer("ws://localhost:8080");
        wss.AddWebSocketService<AvatarService>("/avatar");
        wss.Start();
    }

    void OnDestroy()
    {
        wss.Stop();
    }
}

public class AvatarService : WebSocketBehavior
{
    protected override void OnMessage(MessageEventArgs e)
    {
        var command = JsonUtility.FromJson<AvatarCommand>(e.Data);
        AvatarController.Instance.ExecuteCommand(command);
    }
}
```

### Estrutura de Comando
```csharp
[System.Serializable]
public class AvatarCommand
{
    public string type; // "avatar_control"
    public string emotion;
    public string gesture;
    public bool speak;
    public string speechText;
}
```

## Fase 5 — Python (Cérebro)

### Loop Principal
```python
import asyncio
import websockets
import json

async def main():
    uri = "ws://localhost:8080/avatar"
    
    async with websockets.connect(uri) as websocket:
        while True:
            user_input = await get_user_input()
            
            # Processamento IA
            response = await llm.generate_response(user_input)
            emotion = await detect_emotion(response)
            gesture = decide_gesture(emotion)
            
            # Enviar para Unity
            command = {
                "type": "avatar_control",
                "emotion": emotion,
                "gesture": gesture,
                "speech": response,
                "speak": True
            }
            
            await websocket.send(json.dumps(command))
            
            # Aguardar resposta ou continuar
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
```

## Fase 6 — Integração de Voz (TTS)

### Pipeline de Áudio
1. **Geração**: Python gera arquivo WAV
2. **Transmissão**: Enviar via WebSocket ou HTTP
3. **Reprodução**: Unity carrega e reproduz

### Implementação
```python
import coqui_tts

class TTSManager:
    def __init__(self):
        self.tts = coqui_tts.TTS()
    
    async def generate_speech(self, text: str) -> bytes:
        wav = self.tts.tts(text=text)
        return wav

# No loop principal
audio_data = await tts.generate_speech(response)
command["audio"] = base64.b64encode(audio_data).decode()
```

## Fase 7 — Integração com Streaming

### Configuração OBS
- Captura de janela Unity
- Cena dedicada para avatar
- Sincronização de delay com áudio
- Overlays e efeitos

### Otimizações
- Resolução adequada (720p/1080p)
- Frame rate consistente (30/60 FPS)
- Compressão de vídeo otimizada