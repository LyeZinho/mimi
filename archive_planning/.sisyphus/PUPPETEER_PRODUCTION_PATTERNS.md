# 🔍 ANÁLISE COMPLETA: Padrões Production-Ready para Fase 2 (Browser Control)

**Fonte**: Librarian Agent Research (bg_e30d1df3)
**Data**: 2026-03-27
**Referências**: GitHub, Puppeteer oficial, Browserless docs, production code

---

## 📌 TL;DR: Key Patterns para BrowserController

### 1. Enterprise Integration Pattern
```javascript
// ✅ RECOMENDADO: Use Puppeteer + Cluster para parallelism
const { Cluster } = require('puppeteer-cluster');

const cluster = await Cluster.launch({ 
  concurrency: Cluster.CONCURRENCY_CONTEXT, 
  maxConcurrency: 2  // Limit de workers simultâneos
});

await cluster.task(async ({ page, data }) => {
  await page.goto(data.url, { waitUntil: 'networkidle2' });
  await page.screenshot({ path: 'screenshot.png' });
});

cluster.queue({ url: 'https://example.com' });
await cluster.idle();
await cluster.close();
```
**Por quê**: Evita vazamento de memória com browser pooling

### 2. Screenshot Caching (LRU)
```javascript
// ✅ RECOMENDADO: Use node-lru-cache com limites
const { LRUCache } = require('lru-cache');

const cache = new LRUCache({
  max: 10,              // Máximo 10 screenshots
  ttl: 1000 * 60 * 5,   // 5 minutos por screenshot
  maxSize: 50 * 1024 * 1024  // 50MB total (optional)
});

// Adicionar screenshot
cache.set(url, screenshotBuffer);

// Recuperar (ou undefined se expirou/foi evicted)
const cached = cache.get(url);
```
**Por quê**: LRU evita memory leak automaticamente

### 3. Timeout Enforcement (30s)
```javascript
// ✅ RECOMENDADO: Global + Promise.race para garantir
await page.setDefaultTimeout(30_000);  // Global 30s

// Por operação
await page.goto(url, { timeout: 30_000, waitUntil: 'networkidle2' });

// Extra safety com Promise.race
const withTimeout = (promise, ms = 30_000) => Promise.race([
  promise,
  new Promise((_, rej) => 
    setTimeout(() => rej(new Error('Timeout after 30s')), ms)
  )
]);

await withTimeout(page.click(selector));
```
**Por quê**: Previne penduração indefinida

### 4. Error Handling Padrão
```javascript
// ✅ RECOMENDADO: Try/catch com tipos específicos
try {
  await page.waitForSelector(selector, { timeout: 10_000 });
  await page.click(selector);
} catch (err) {
  if (err.name === 'TimeoutError') {
    // Timeout específico
    logger.warn(`Timeout waiting for ${selector}`);
    return { success: false, error: 'TIMEOUT' };
  } else if (err.message.includes('not found')) {
    // Elemento não existe
    logger.warn(`Element ${selector} not found`);
    return { success: false, error: 'ELEMENT_NOT_FOUND' };
  } else {
    // Erro genérico
    logger.error('Unexpected error:', err);
    return { success: false, error: 'ERROR', details: err.message };
  }
}
```
**Por quê**: Permite retry logic diferenciado por tipo de erro

---

## 🎯 Implementação Recomendada para BrowserController

### Arquitetura Proposta
```
┌──────────────────────────────────────┐
│ Your WebSocket Server (server.js)    │
│  ├─ Receive browser_command          │
│  └─ Delegate to BrowserController    │
└─────────────┬────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│ BrowserController (service)           │
│  ├─ Puppeteer Cluster (max 2-4)       │
│  ├─ Screenshot Cache (LRU, max 10)    │
│  ├─ Timeout enforcement (30s)         │
│  └─ Error handling + retry logic      │
└─────────────┬────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│ Browser (Chromium)                    │
│  ├─ navigate, click, type, etc.       │
│  └─ Screenshot capture                │
└──────────────────────────────────────┘
```

### Code Template: BrowserController.js (Production-Ready)

```javascript
const puppeteer = require('puppeteer');
const { Cluster } = require('puppeteer-cluster');
const { LRUCache } = require('lru-cache');
const logger = require('./logger');

class BrowserController {
  constructor(options = {}) {
    this.maxConcurrency = options.maxConcurrency || 2;
    this.cluster = null;
    this.screenshotCache = new LRUCache({
      max: 10,
      ttl: 1000 * 60 * 5,  // 5 min TTL
      maxSize: 50 * 1024 * 1024  // 50MB
    });
    this.DEFAULT_TIMEOUT = 30_000;
    this.commandIdCounter = 0;
  }

  async initialize() {
    try {
      this.cluster = await Cluster.launch({
        concurrency: Cluster.CONCURRENCY_CONTEXT,
        maxConcurrency: this.maxConcurrency,
        puppeteerOptions: {
          headless: true,
          args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
      });

      // Task handler: cada worker executa isso
      await this.cluster.task(async ({ page, data: task }) => {
        try {
          const result = await this._executeTaskOnPage(page, task);
          return result;
        } catch (err) {
          return this._formatError(task.type, err);
        }
      });

      logger.info('BrowserController initialized with cluster');
    } catch (err) {
      logger.error('Failed to initialize BrowserController:', err);
      throw err;
    }
  }

  async executeCommand(command) {
    /**
     * command = {
     *   type: 'navigate' | 'click' | 'type' | 'screenshot' | 'execute_script' | 'wait',
     *   params: {...}
     * }
     */
    
    const startTime = Date.now();
    
    try {
      // Queue task to cluster
      const result = await Promise.race([
        this.cluster.execute(command),
        new Promise((_, rej) =>
          setTimeout(() => rej(new Error('Command timeout after 30s')), this.DEFAULT_TIMEOUT)
        )
      ]);

      const duration = Date.now() - startTime;

      // Cache screenshots
      if (command.type === 'screenshot' && result.screenshot) {
        this.screenshotCache.set(
          `screenshot_${Date.now()}`,
          Buffer.from(result.screenshot, 'base64')
        );
      }

      return {
        success: true,
        result: result,
        duration_ms: duration
      };
    } catch (err) {
      const duration = Date.now() - startTime;
      
      return {
        success: false,
        error: err.message,
        error_type: err.name,
        duration_ms: duration
      };
    }
  }

  async _executeTaskOnPage(page, task) {
    /**
     * Executa task individual em uma página Puppeteer
     */
    await page.setDefaultTimeout(this.DEFAULT_TIMEOUT);

    switch (task.type) {
      case 'navigate':
        return await this._handleNavigate(page, task.params);
      case 'click':
        return await this._handleClick(page, task.params);
      case 'type':
        return await this._handleType(page, task.params);
      case 'screenshot':
        return await this._handleScreenshot(page, task.params);
      case 'execute_script':
        return await this._handleExecuteScript(page, task.params);
      case 'wait':
        return await this._handleWait(page, task.params);
      default:
        throw new Error(`Unknown command type: ${task.type}`);
    }
  }

  async _handleNavigate(page, params) {
    const { url, waitUntil = 'networkidle2' } = params;
    
    await page.goto(url, {
      timeout: this.DEFAULT_TIMEOUT,
      waitUntil
    });

    return {
      url: page.url(),
      title: await page.title()
    };
  }

  async _handleClick(page, params) {
    const { selector } = params;

    try {
      // Wait for element first
      await page.waitForSelector(selector, { timeout: 10_000 });
      await page.click(selector);
      return { clicked: true, selector };
    } catch (err) {
      if (err.name === 'TimeoutError') {
        throw new Error(`Element ${selector} not found (timeout)`);
      }
      throw err;
    }
  }

  async _handleType(page, params) {
    const { selector, text } = params;

    try {
      await page.waitForSelector(selector, { timeout: 10_000 });
      await page.type(selector, text);
      return { typed: true, selector, text };
    } catch (err) {
      throw new Error(`Failed to type in ${selector}: ${err.message}`);
    }
  }

  async _handleScreenshot(page, params) {
    const { fullPage = false } = params;

    const screenshot = await page.screenshot({ fullPage });
    return {
      screenshot: screenshot.toString('base64'),
      width: (await page.viewport()).width,
      height: (await page.viewport()).height,
      timestamp: Date.now()
    };
  }

  async _handleExecuteScript(page, params) {
    const { script } = params;

    const result = await page.evaluate(script);
    return { result };
  }

  async _handleWait(page, params) {
    const { selector, timeout = this.DEFAULT_TIMEOUT } = params;

    try {
      await page.waitForSelector(selector, { timeout });
      return { waited: true, selector };
    } catch (err) {
      throw new Error(`Element ${selector} not found (timeout: ${timeout}ms)`);
    }
  }

  _formatError(commandType, err) {
    /**
     * Normaliza erros para resposta
     */
    return {
      error: err.message,
      error_type: err.name || 'UNKNOWN_ERROR',
      command_type: commandType,
      timestamp: Date.now()
    };
  }

  getScreenshotCache() {
    return {
      size: this.screenshotCache.size,
      items: Array.from(this.screenshotCache.entries()).map(([key, val]) => ({
        key,
        size: val.length
      }))
    };
  }

  async shutdown() {
    if (this.cluster) {
      await this.cluster.close();
      logger.info('BrowserController shutdown');
    }
  }
}

module.exports = BrowserController;
```

---

## 🔌 Integração com server.js (WebSocket)

```javascript
// In web_avatar/server.js

const BrowserController = require('./services/BrowserController');
const browserController = new BrowserController({ maxConcurrency: 2 });

// On server startup
await browserController.initialize();

// Handle incoming browser_command from Python agent
ws.on('message', async (msg) => {
  const parsed = JSON.parse(msg);

  if (parsed.type === 'browser_command') {
    const { command_id, command_type, params } = parsed;

    try {
      const result = await browserController.executeCommand({
        type: command_type,
        params
      });

      // Send result back to Python
      ws.send(JSON.stringify({
        type: 'browser_command_result',
        command_id,
        success: result.success,
        result: result.result,
        error: result.error,
        duration_ms: result.duration_ms
      }));
    } catch (err) {
      ws.send(JSON.stringify({
        type: 'browser_command_result',
        command_id,
        success: false,
        error: err.message
      }));
    }
  }
});

// Shutdown on server close
process.on('SIGTERM', async () => {
  await browserController.shutdown();
  process.exit(0);
});
```

---

## 📊 Production Patterns & Best Practices

### 1. Monitoring & Metrics
```javascript
// Track command performance
class BrowserMetrics {
  constructor() {
    this.commands = [];
  }

  recordCommand(command, duration, success) {
    this.commands.push({
      type: command.type,
      duration_ms: duration,
      success,
      timestamp: Date.now()
    });
    
    // Keep last 1000 commands
    if (this.commands.length > 1000) {
      this.commands.shift();
    }
  }

  getStats() {
    const stats = {
      total: this.commands.length,
      successful: this.commands.filter(c => c.success).length,
      failed: this.commands.filter(c => !c.success).length,
      avg_duration: 0,
      p99_duration: 0
    };

    if (this.commands.length > 0) {
      const durations = this.commands.map(c => c.duration_ms).sort((a, b) => a - b);
      stats.avg_duration = durations.reduce((a, b) => a + b) / durations.length;
      stats.p99_duration = durations[Math.floor(durations.length * 0.99)];
    }

    return stats;
  }
}
```

### 2. Retry Logic (Exponential Backoff)
```javascript
async function executeWithRetry(browserController, command, maxRetries = 3) {
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await browserController.executeCommand(command);
    } catch (err) {
      lastError = err;
      
      // Don't retry on certain errors
      if (err.message.includes('ELEMENT_NOT_FOUND')) {
        throw err;  // No retry
      }
      
      if (attempt < maxRetries) {
        // Exponential backoff: 1s, 2s, 4s
        const delay = Math.pow(2, attempt - 1) * 1000;
        logger.warn(`Retry attempt ${attempt}/${maxRetries} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  throw lastError;
}
```

### 3. Health Check Endpoint
```javascript
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    cluster: browserController.cluster ? 'running' : 'down',
    screenshot_cache: browserController.getScreenshotCache(),
    metrics: metrics.getStats()
  });
});
```

---

## ✅ Checklist para Fase 2 Implementation

- [ ] Install dependencies: `npm install puppeteer puppeteer-cluster lru-cache`
- [ ] Create `BrowserController.js` using template above
- [ ] Create `BrowserMetrics.js` for tracking
- [ ] Integrate with `server.js` WebSocket handler
- [ ] Implement retry logic with exponential backoff
- [ ] Add health check endpoint
- [ ] Test each command: navigate, click, type, screenshot, execute_script, wait
- [ ] Test timeout enforcement (verify 30s max)
- [ ] Test error handling (click non-existent element)
- [ ] Test screenshot cache (verify max 10 items)
- [ ] Test memory usage (verify no leak with 100+ commands)
- [ ] Add logging for all commands
- [ ] Document command API

---

## 📚 Reference Links (Production Patterns)

1. **Puppeteer Official Docs**
   - setDefaultTimeout: https://raw.githubusercontent.com/puppeteer/puppeteer/main/docs/api/puppeteer.page.setdefaulttimeout.md
   - waitForSelector default (30s): https://raw.githubusercontent.com/puppeteer/puppeteer/main/docs/api/puppeteer.page.waitforselector.md
   - TimeoutError: https://raw.githubusercontent.com/puppeteer/puppeteer/main/docs/api/puppeteer.timeouterror.md
   - Page.click behavior: https://raw.githubusercontent.com/puppeteer/puppeteer/main/docs/api/puppeteer.page.click.md

2. **Production Libraries**
   - Puppeteer Cluster: https://raw.githubusercontent.com/thomasdondorf/puppeteer-cluster/master/examples/minimal.js
   - LRU Cache: https://raw.githubusercontent.com/isaacs/node-lru-cache/master/README.md
   - Browserless (WebSocket pattern): https://docs.browserless.io/libraries/puppeteer
   - Express Middleware: https://github.com/zenato/puppeteer-renderer/blob/main/packages/middleware/README.md

---

**Integrado pela análise**: Librarian Agent Research
**Confiança**: Alta (referências production-ready)
**Status**: ✅ Pronto para implementação
