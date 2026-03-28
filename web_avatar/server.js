// Servidor WebSocket para Mimi Web Avatar (Node.js)
// Basta rodar: node server.js

const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');
const PORT = 8765;

// Estado global do avatar
let avatarState = {
  model: 'Mimi.vrm',
  expression: 'neutral',
  animation: null,
  animationLoop: true,
  speaking: false,
  camera: {
    position: { x: 0, y: 1.4, z: 2 },
    target: { x: 0, y: 1.2, z: 0 }
  },
  background: '#1a1a2e',
  lastUpdate: Date.now(),
};

// LLM Configuration state
let llmConfig = {
  model: process.env.LLM_MODEL || 'phi3:mini',
  temperature: parseFloat(process.env.LLM_TEMPERATURE || '0.7'),
  max_tokens: parseInt(process.env.LLM_MAX_TOKENS || '1024'),
  top_p: parseFloat(process.env.LLM_TOP_P || '0.9'),
  top_k: parseInt(process.env.LLM_TOP_K || '40'),
};

// Função para broadcast para todos os clientes (exceto opcionalmente o remetente)
function broadcastState(exceptWs = null) {
  const msg = JSON.stringify({ type: 'state', state: avatarState });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN && client !== exceptWs) {
      client.send(msg);
    }
  });
}

// Broadcast LLM config to all clients
function broadcastLLMConfig(exceptWs = null) {
  const msg = JSON.stringify({ type: 'llm_config', config: llmConfig });
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN && client !== exceptWs) {
      client.send(msg);
    }
  });
}

// Função para atualizar o estado global
function updateState(updates) {
  avatarState = { ...avatarState, ...updates, lastUpdate: Date.now() };
}

// Mock de integração IA (substitua por chamada real se desejar)
async function askAI(message) {
  // Aqui você pode integrar com Ollama, OpenAI, etc.
  // Exemplo mock:
  return {
    text: `Mimi (IA): Você disse "${message}"`,
    intent: 'speak',
    emotion: 'neutral',
  };
}

// Servidor HTTP para integração REST e upload de arquivos
const server = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/chat') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const { message } = JSON.parse(body);
        const aiResp = await askAI(message);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(aiResp));
      } catch (e) {
        res.writeHead(400);
        res.end('Bad Request');
      }
    });
    return;
  }

  // Upload de arquivos VRM/FBX
  if (req.method === 'POST' && req.url.startsWith('/upload')) {
    // Exemplo: /upload/model ou /upload/animation
    const type = req.url.includes('model') ? 'model' : req.url.includes('animation') ? 'animation' : null;
    if (!type) {
      res.writeHead(400);
      res.end('Tipo de upload inválido');
      return;
    }
    const dir = type === 'model' ? path.join(__dirname, 'public', 'models') : path.join(__dirname, 'public', 'animations');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    // Recebe o arquivo inteiro em buffer
    const chunks = [];
    req.on('data', chunk => chunks.push(chunk));
    req.on('end', () => {
      const buffer = Buffer.concat(chunks);
      // Nome do arquivo via header ou fallback
      const filename = decodeURIComponent(req.headers['x-filename'] || `file_${Date.now()}`);
      const safeName = filename.replace(/[^a-zA-Z0-9_.-]/g, '_');
      const filePath = path.join(dir, safeName);
      fs.writeFileSync(filePath, buffer);
      // Gera URL pública
      const publicUrl = type === 'model' ? `/models/${safeName}` : `/animations/${safeName}`;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ url: publicUrl }));
    });
    return;
  }

  if (req.url === '/mirror.html' || req.url === '/mirror') {
    const mirrorHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mimi Mirror Stream - OBS Source</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background-color: #1a1a2e; font-family: 'Segoe UI', sans-serif; overflow: hidden; }
        #container { width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; }
        #mirror-canvas { max-width: 100%; max-height: 100%; object-fit: contain; background-color: #0f0f1e; }
        #status { position: absolute; top: 20px; left: 20px; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5); z-index: 100; }
        #status.connected { background-color: rgba(34, 197, 94, 0.9); color: #fff; }
        #status.connecting { background-color: rgba(59, 130, 246, 0.9); color: #fff; }
        #status.disconnected { background-color: rgba(239, 68, 68, 0.9); color: #fff; }
        #fps-counter { position: absolute; bottom: 20px; right: 20px; padding: 8px 12px; background-color: rgba(0, 0, 0, 0.7); color: #22c55e; font-size: 12px; font-family: 'Courier New', monospace; border-radius: 4px; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5); }
        #loading-spinner { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.2); border-top: 3px solid #22c55e; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { 0% { transform: translate(-50%, -50%) rotate(0deg); } 100% { transform: translate(-50%, -50%) rotate(360deg); } }
        #loading-spinner.hidden { display: none; }
    </style>
</head>
<body>
    <div id="container">
        <canvas id="mirror-canvas"></canvas>
        <div id="loading-spinner"></div>
    </div>
    <div id="status" class="connecting">Waiting for connection...</div>
    <div id="fps-counter">FPS: 0 | Frames: 0</div>
    <script>
        class MirrorStreamClient {
            constructor() {
                this.ws = null;
                this.canvas = document.getElementById('mirror-canvas');
                this.ctx = this.canvas.getContext('2d');
                this.statusEl = document.getElementById('status');
                this.spinnerEl = document.getElementById('loading-spinner');
                this.fpsEl = document.getElementById('fps-counter');
                this.frameCount = 0;
                this.fps = 0;
                this.lastFpsUpdate = Date.now();
                this.setupCanvas();
                this.connect();
            }
            setupCanvas() {
                this.canvas.width = window.innerWidth;
                this.canvas.height = window.innerHeight;
                window.addEventListener('resize', () => {
                    this.canvas.width = window.innerWidth;
                    this.canvas.height = window.innerHeight;
                });
            }
            connect() {
                const wsUrl = this.getWebSocketUrl();
                console.log('[Mirror] Connecting to ' + wsUrl);
                try {
                    this.ws = new WebSocket(wsUrl);
                    this.ws.onopen = () => this.onOpen();
                    this.ws.onmessage = (event) => this.onMessage(event);
                    this.ws.onerror = (error) => this.onError(error);
                    this.ws.onclose = () => this.onClose();
                } catch (error) {
                    console.error('[Mirror] WebSocket creation failed:', error);
                    this.setStatus('disconnected', 'Connection failed');
                }
            }
            getWebSocketUrl() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const host = window.location.hostname;
                return protocol + '//' + host + ':8765';
            }
            onOpen() {
                console.log('[Mirror] WebSocket connected');
                this.setStatus('connected', 'Live');
                this.spinnerEl.classList.add('hidden');
                this.ws.send(JSON.stringify({ type: 'webrtc_mirror_request' }));
            }
            onMessage(event) {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'mirror_frame' && msg.frame_data) {
                        this.renderFrame(msg.frame_data);
                        this.updateFps();
                    }
                } catch (error) {
                    console.error('[Mirror] Failed to parse message:', error);
                }
            }
            renderFrame(frameData) {
                const img = new Image();
                img.onload = () => {
                    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
                };
                img.onerror = () => {
                    console.error('[Mirror] Failed to load frame image');
                };
                img.src = frameData;
            }
            updateFps() {
                this.frameCount++;
                const now = Date.now();
                const elapsed = now - this.lastFpsUpdate;
                if (elapsed >= 1000) {
                    this.fps = Math.round(this.frameCount * 1000 / elapsed);
                    this.fpsEl.textContent = 'FPS: ' + this.fps + ' | Frames: ' + this.frameCount;
                    this.frameCount = 0;
                    this.lastFpsUpdate = now;
                }
            }
            onError(error) {
                console.error('[Mirror] WebSocket error:', error);
                this.setStatus('disconnected', 'Connection error');
            }
            onClose() {
                console.warn('[Mirror] WebSocket closed, attempting reconnect...');
                this.setStatus('disconnected', 'Connection lost. Reconnecting...');
                this.spinnerEl.classList.remove('hidden');
                setTimeout(() => this.connect(), 2000);
            }
            setStatus(state, message) {
                this.statusEl.className = state;
                this.statusEl.textContent = message;
            }
        }
        window.addEventListener('DOMContentLoaded', () => {
            new MirrorStreamClient();
        });
    </script>
</body>
</html>`;
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(mirrorHtml);
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  console.log('Cliente conectado');
  ws.send(JSON.stringify({ type: 'state', state: avatarState }));
  ws.send(JSON.stringify({ type: 'llm_config', config: llmConfig }));

  ws.on('message', async (data) => {
    let msg;
    try {
      msg = JSON.parse(data);
    } catch (e) {
      console.error('Mensagem inválida:', data);
      return;
    }

    // Manipulação de comandos
    switch (msg.type) {
      case 'set_model':
        if (msg.model) {
          updateState({ model: msg.model });
          // Sempre faz broadcast para todos, inclusive para quem enviou
          wss.clients.forEach((client) => {
            if (client.readyState === WebSocket.OPEN) {
              client.send(JSON.stringify({ type: 'state', state: avatarState }));
            }
          });
        }
        break;
      case 'set_expression':
        if (msg.expression) {
          updateState({ expression: msg.expression });
          broadcastState();
        }
        break;
      case 'set_animation':
        // Permite animation ser null para limpar animação
        if ('animation' in msg) {
          updateState({ animation: msg.animation, animationLoop: !!msg.loop });
          broadcastState();
        }
        break;
      case 'set_camera':
        if (msg.camera) {
          updateState({ camera: msg.camera });
          broadcastState();
        }
        break;
      case 'set_background':
        if (msg.background) {
          updateState({ background: msg.background });
          broadcastState();
        }
        break;
      case 'set_speaking':
        updateState({ speaking: !!msg.speaking });
        broadcastState();
        break;
      case 'state': // Atualização de estado completa
        if (msg.state) {
          updateState(msg.state);
          broadcastState(ws); // não ecoa para quem enviou
        }
        break;
      case 'chat': // Forward to Agent
        if (msg.text || msg.message) {
          // Broadcast to all clients (Agent should pick this up)
          const text = msg.text || msg.message;
          console.log(`Chat forwarding: ${text}`);
          broadcastState(ws); // Broadcasts state, but we need to broadcast the EVENT

          // Manual broadcast of the chat event
          const chatMsg = JSON.stringify({ type: 'agent_input', text: text, sender: 'user' });
          let broadcastCount = 0;
          wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN && client !== ws) {
              console.log(`[BROADCAST] Sending agent_input to client`);
              client.send(chatMsg);
              broadcastCount++;
            }
          });
          console.log(`[BROADCAST] Forwarded to ${broadcastCount} clients`);
        }
        break;

      case 'audio_chunk': // Forward audio to Agent for VAD+STT
        if (msg.data && msg.sample_rate) {
          console.log(`[Server] Received audio_chunk: ${msg.data.length} bytes @ ${msg.sample_rate}Hz`);
          console.log(`[Server] Total connected clients: ${wss.clients.size}`);
          const audioMsg = JSON.stringify({
            type: 'audio_chunk',
            data: msg.data,
            sample_rate: msg.sample_rate
          });
          let sentCount = 0;
          wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN && client !== ws) {
              client.send(audioMsg);
              sentCount++;
            }
          });
          console.log(`[Server] Forwarded audio_chunk to ${sentCount} agent client(s)`);
        }
        break;

      case 'agent_response': // Response from Agent
        broadcastState();
        const responseMsg = JSON.stringify({
          type: 'chat_response',
          text: msg.text,
          sender: 'Mimi'
        });
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(responseMsg);
          }
        });
        break;

      case 'processing_update': // Processing stage updates from Agent
        const processingMsg = JSON.stringify({
          type: 'processing_update',
          stage: msg.stage,
          text: msg.text,
          intent: msg.intent,
          plan: msg.plan,
          sentiment: msg.sentiment,
          emotion: msg.emotion
        });
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN) {
            client.send(processingMsg);
          }
        });
        break;

      case 'agent_input':
        // Message from agent or internal routing - just log
        console.log(`Agent input forwarded: ${msg.text}`);
        break;

      case 'set_llm_model':
        if (msg.model) {
          const previousModel = llmConfig.model;
          llmConfig.model = msg.model;
          console.log(`LLM model changed: ${previousModel} -> ${msg.model}`);
          broadcastLLMConfig();
        }
        break;

      case 'set_llm_temperature':
        if (msg.temperature !== undefined && msg.temperature >= 0 && msg.temperature <= 2) {
          llmConfig.temperature = parseFloat(msg.temperature);
          console.log(`LLM temperature set to: ${llmConfig.temperature}`);
          broadcastLLMConfig();
        }
        break;

      case 'set_llm_max_tokens':
        if (msg.max_tokens && msg.max_tokens > 0) {
          llmConfig.max_tokens = parseInt(msg.max_tokens);
          console.log(`LLM max_tokens set to: ${llmConfig.max_tokens}`);
          broadcastLLMConfig();
        }
        break;

      case 'set_llm_top_p':
        if (msg.top_p !== undefined && msg.top_p >= 0 && msg.top_p <= 1) {
          llmConfig.top_p = parseFloat(msg.top_p);
          console.log(`LLM top_p set to: ${llmConfig.top_p}`);
          broadcastLLMConfig();
        }
        break;

      case 'set_llm_top_k':
        if (msg.top_k && msg.top_k > 0) {
          llmConfig.top_k = parseInt(msg.top_k);
          console.log(`LLM top_k set to: ${llmConfig.top_k}`);
          broadcastLLMConfig();
        }
        break;

      case 'set_llm_config':
        if (msg.config) {
          const updates = {};
          if (msg.config.model) updates.model = msg.config.model;
          if (msg.config.temperature !== undefined) updates.temperature = parseFloat(msg.config.temperature);
          if (msg.config.max_tokens) updates.max_tokens = parseInt(msg.config.max_tokens);
          if (msg.config.top_p !== undefined) updates.top_p = parseFloat(msg.config.top_p);
          if (msg.config.top_k) updates.top_k = parseInt(msg.config.top_k);
          llmConfig = { ...llmConfig, ...updates };
          console.log('LLM config updated:', updates);
          broadcastLLMConfig();
        }
        break;

      case 'get_llm_config':
        ws.send(JSON.stringify({ type: 'llm_config', config: llmConfig }));
        break;

      case 'webrtc_mirror_request':
        console.log('[MIRROR] WebRTC mirror stream requested');
        ws.send(JSON.stringify({
          type: 'webrtc_mirror_offer',
          message: 'WebRTC mirror stream ready. Client should initiate peer connection.'
        }));
        break;

      case 'webrtc_signal':
        if (msg.to) {
          console.log('[MIRROR] Forwarding WebRTC signal:', msg.type);
          const targetClient = Array.from(wss.clients).find(c => c === msg.to);
          if (targetClient && targetClient.readyState === WebSocket.OPEN) {
            targetClient.send(JSON.stringify({
              type: 'webrtc_signal',
              signal: msg.signal,
              from: ws
            }));
          }
        } else {
          console.log('[MIRROR] Broadcasting WebRTC signal to all clients');
          wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN && client !== ws) {
              client.send(JSON.stringify({
                type: 'webrtc_signal',
                signal: msg.signal,
                from: 'mirror_stream'
              }));
            }
          });
        }
        break;

      case 'mirror_frame':
        if (msg.frame_data) {
          console.debug('[MIRROR] Received frame from client, broadcasting');
          wss.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN && client !== ws) {
              client.send(JSON.stringify({
                type: 'mirror_frame',
                frame_data: msg.frame_data,
                timestamp: Date.now()
              }));
            }
          });
        }
        break;

      case 'avatar_control':
        // Forward emotion/gesture/speaking commands from Python agent to frontend
        console.log('[AVATAR] Control message:', msg.emotion || msg.gesture || 'unknown');
        wss.clients.forEach(client => {
          if (client.readyState === WebSocket.OPEN && client !== ws) {
            client.send(JSON.stringify(msg));
          }
        });
        break;

      default:
        console.warn('Tipo de mensagem desconhecido:', msg.type);
    }
  });

  ws.on('close', () => {
    console.log('Cliente desconectado');
  });
});

server.listen(PORT, () => {
  console.log(`WebSocket/HTTP server rodando em ws://localhost:${PORT}`);
});
