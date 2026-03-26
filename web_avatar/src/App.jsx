
import React, { useState, useEffect, useRef } from 'react';
import AvatarCanvas from './components/AvatarCanvas';
import AnimationControls from './components/AnimationControls';
import ExpressionControls from './components/ExpressionControls';
import WebSocketStatus from './components/WebSocketStatus';
import ModelUpload from './components/ModelUpload';
import ChatInterface from './components/ChatInterface';
import { WebSocketClient } from './logic/WebSocketClient';
import { AvatarStateManager } from './logic/AvatarStateManager';
import GUI from 'lil-gui';
import './style.css';

export default function App() {
  const [modelUrl, setModelUrl] = useState(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [isObsMode, setIsObsMode] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [fps, setFps] = useState(0);

  // Logic instances
  const wsClientRef = useRef(null);
  const stateManagerRef = useRef(null);
  const viewerRef = useRef(null);
  const guiRef = useRef(null);

  useEffect(() => {
    // Check for OBS mode
    const params = new URLSearchParams(window.location.search);
    if (params.get('mode') === 'obs') {
      setIsObsMode(true);
      document.body.style.background = 'transparent';
    }

    // Initialize Logic Layer
    const wsClient = new WebSocketClient('ws://localhost:8765');
    const stateManager = new AvatarStateManager(wsClient);

    wsClientRef.current = wsClient;
    stateManagerRef.current = stateManager;

    // Setup WebSocket listeners
    wsClient.onStatusChange((status) => {
      setWsStatus(status);
      if (status === 'connected') {
        stateManager.isController = true;
      }
    });

    wsClient.onMessage((msg) => {
      // Handle incoming messages
      if (msg.type === 'avatar_control' && viewerRef.current) {
        const exprCtrl = viewerRef.current.expressionController;
        if (!exprCtrl) return;

        if (msg.emotion) {
          exprCtrl.setExpression(msg.emotion);
          // Sync state
          stateManager.setExpression(msg.emotion);
        }
        if (msg.speak) {
          if (msg.speech_text) {
            const duration = msg.speech_text.length * 50;
            exprCtrl.speak(duration);
            stateManager.setSpeaking(true);
            setTimeout(() => stateManager.setSpeaking(false), duration);
          }
        }
      }

      if (msg.type === 'chat_response') {
        console.log('[App] Chat response from agent:', msg.text);
        setChatMessages(prev => [...prev, { sender: 'agent', text: msg.text }]);
        if (window.speechSynthesis) {
          const utterance = new SpeechSynthesisUtterance(msg.text);
          utterance.lang = 'pt-BR';
          window.speechSynthesis.speak(utterance);
        }
      }
    });

    // Connect
    wsClient.connect().catch(err => {
      console.warn("WS Connect info", err); // Changed to warn to reduce noise
    });

    return () => {
      wsClient.disconnect();
    };
  }, []);

  // Quando um modelo é carregado do upload, sincroniza
  const handleModelLoaded = (url) => {
    setModelUrl(url);
    if (wsClientRef.current) {
      wsClientRef.current.send({ type: 'set_model', model: url });
    }
  };

  // Callback quando o viewer termina de carregar o modelo
  const handleModelLoadedInViewer = (vrm) => {
    console.log('[App] Modelo carregado no viewer:', vrm);
  };

  const handleViewerReady = (viewer) => {
    viewerRef.current = viewer;
    // Initialize animations
    if (viewer && viewer.animationManager) {
      viewer.animationManager.loadAnimation('Idle', '/animations/Idle.fbx')
        .then(() => {
          viewer.animationManager.play('Idle');
          if (stateManagerRef.current) stateManagerRef.current.setAnimation('Idle');
        })
        .catch(e => console.warn("Idle anim missing", e));
    }
  };

  const handleExpressionChange = (expression) => {
    if (viewerRef.current && viewerRef.current.expressionController) {
      viewerRef.current.expressionController.setExpression(expression);
      if (stateManagerRef.current) stateManagerRef.current.setExpression(expression);
    }
  };

  const handleSendMessage = (text) => {
    setChatMessages(prev => [...prev, { sender: 'user', text }]);
    if (wsClientRef.current) {
      wsClientRef.current.send({ type: 'chat', text: text });
    }
  };

  const handleAnimationChange = (anim) => {
    if (viewerRef.current && viewerRef.current.animationManager) {
      if (typeof anim === 'string') {
        const name = anim;
        const url = `/animations/${anim}.fbx`;
        viewerRef.current.animationManager.loadAnimation(name, url)
          .then(() => {
            viewerRef.current.animationManager.play(name);
            if (stateManagerRef.current) stateManagerRef.current.setAnimation({ name, url });
            // Envia para o backend o objeto completo
            if (wsClientRef.current) {
              wsClientRef.current.send({ type: 'set_animation', animation: { name, url } });
            }
          })
          .catch(e => console.error("Anim load failed", e));
      } else if (anim && anim.url) {
        viewerRef.current.animationManager.loadAnimation(anim.name, anim.url)
          .then(() => {
            viewerRef.current.animationManager.play(anim.name);
            if (wsClientRef.current) {
              wsClientRef.current.send({ type: 'set_animation', animation: { name: anim.name, url: anim.url } });
            }
          });
      }
    }
  };

  const handlePoseChange = (pose) => {
    if (viewerRef.current && viewerRef.current.animationManager) {
      viewerRef.current.animationManager.setPose(pose);
    }
  };

  if (isObsMode) {
    return (
      <div className="obs-container">
        <AvatarCanvas
          modelUrl={modelUrl}
          onViewerReady={handleViewerReady}
          onModelLoaded={handleModelLoadedInViewer}
        />
      </div>
    );
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo">Mimi Dev Console</div>
        <div className="status-bar">
          <WebSocketStatus status={wsStatus} />
          <span className="fps-counter">FPS: {fps}</span>
        </div>
      </header>

      <main className="main-layout">
        <aside className="sidebar left-sidebar">
          <h3>Model & View</h3>
          <ModelUpload onModelLoaded={setModelUrl} />
          <div className="panel">
            <h4>Camera Controls</h4>
            <p>Wait for CameraWidget...</p>
          </div>
        </aside>

        <section className="viewport-area">
          <AvatarCanvas
            modelUrl={modelUrl}
            onViewerReady={handleViewerReady}
            onModelLoaded={handleModelLoadedInViewer}
            onCameraChange={(cam) => {
              if (stateManagerRef.current && stateManagerRef.current.isController) {
                stateManagerRef.current.setCamera(cam.position, cam.target);
              }
            }}
          />
        </section>

        <aside className="sidebar right-sidebar">
          <h3>Controls</h3>
          <AnimationControls
            onAnimationChange={handleAnimationChange}
            onPoseChange={handlePoseChange}
          />
          <div className="divider"></div>
          <ExpressionControls onExpressionChange={handleExpressionChange} />

          <div className="divider"></div>
          <h3>Chat & Log</h3>
          <div className="chat-panel">
            <ChatInterface onSendMessage={handleSendMessage} messages={chatMessages} />
          </div>
        </aside>
      </main>
    </div>
  );
}
