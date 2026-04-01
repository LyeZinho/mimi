# Organização de Projeto

## Estrutura Geral

```
📁 projeto_avatar/
├── 📁 python/           # Cérebro IA
│   ├── 📁 agent/
│   │   ├── llm.py       # Cliente LLM
│   │   ├── emotions.py  # Análise de emoções
│   │   ├── memory.py    # Sistema de memória
│   │   ├── tts.py       # Text-to-Speech
│   │   ├── unity_client.py  # Comunicação com Unity
│   │   └── main.py      # Loop principal
│   ├── 📁 config/       # Configurações
│   ├── 📁 utils/        # Utilitários
│   └── requirements.txt
│
├── 📁 unity/            # Corpo (Avatar Engine)
│   ├── 📁 Assets/
│   │   ├── 📁 Scripts/
│   │   │   ├── WebSocketServer.cs
│   │   │   ├── AvatarController.cs
│   │   │   ├── ExpressionController.cs
│   │   │   ├── LipSyncController.cs
│   │   │   └── CameraController.cs
│   │   ├── 📁 Models/   # Arquivos VRM
│   │   ├── 📁 Scenes/   # Cenas Unity
│   │   └── 📁 Animators/# Animator Controllers
│   ├── 📁 Packages/     # UniVRM, etc.
│   └── 📁 ProjectSettings/
│
├── 📁 docs/             # Documentação
│   ├── 📁 avatar_architecture/
│   └── 📁 api/
│
├── 📁 tests/            # Testes
├── 📁 tools/            # Scripts de build/deploy
└── README.md
```

## Detalhamento por Camada

### Python (Cérebro)

#### agent/llm.py
```python
class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    async def generate_response(self, prompt: str, context: dict) -> str:
        # Implementação da geração de resposta
        pass
```

#### agent/emotions.py
```python
class EmotionAnalyzer:
    def __init__(self):
        # Carregar modelo de análise de emoções
        pass
    
    def analyze_text(self, text: str) -> str:
        # Retornar emoção detectada: happy, sad, angry, etc.
        pass
```

#### agent/unity_client.py
```python
class UnityClient:
    def __init__(self, uri: str = "ws://localhost:8080/avatar"):
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
    
    async def send_command(self, command: dict):
        if self.websocket:
            await self.websocket.send(json.dumps(command))
```

### Unity (Corpo)

#### Scripts/WebSocketServer.cs
```csharp
public class WebSocketServer : MonoBehaviour
{
    [SerializeField] private int port = 8080;
    private WebSocketServer wss;
    
    void Start()
    {
        wss = new WebSocketServer($"ws://localhost:{port}");
        wss.Start();
    }
}
```

#### Scripts/AvatarController.cs
```csharp
public class AvatarController : MonoBehaviour
{
    public static AvatarController Instance { get; private set; }
    
    [SerializeField] private Animator animator;
    [SerializeField] private ExpressionController expressionController;
    
    void Awake()
    {
        Instance = this;
    }
    
    public void ExecuteCommand(AvatarCommand command)
    {
        // Executar comando recebido
        SetEmotion(command.emotion);
        PlayGesture(command.gesture);
        
        if (command.speak)
        {
            Speak(command.speechText);
        }
    }
    
    private void SetEmotion(string emotion)
    {
        // Mapear emoção para expressão
        expressionController.SetExpression(emotion, 1f);
    }
    
    private void PlayGesture(string gesture)
    {
        animator.SetTrigger(gesture);
    }
}
```

## Configuração e Build

### Ambiente de Desenvolvimento
- **Python**: Virtual environment com requirements.txt
- **Unity**: Projeto versionado com Git LFS para assets grandes
- **Comunicação**: Porta dedicada (8080) para WebSocket

### Build e Deploy
- **Python**: Package como executável ou container Docker
- **Unity**: Build como aplicação standalone
- **Integração**: Scripts para iniciar ambos os componentes

### Versionamento
- Usar Git para controle de versão
- Branches separados para Python e Unity
- Tags para releases sincronizados