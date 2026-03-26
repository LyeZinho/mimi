// Servidor WebSocket para Mimi Web Avatar (Node.js)
// Basta rodar: node server.js

const WebSocket = require('ws');
const http = require('http');
const fs = require('fs');
const path = require('path');
const PORT = 8765;

// Estado global do avatar
let avatarState = {
  model: null,
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

      case 'agent_response': // Response from Agent
        // Broadcast to frontend
        broadcastState();
        // Also send specific chat response to all (or back to sender if we tracked ID)
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
