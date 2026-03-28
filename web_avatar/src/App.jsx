import React, { useState, useEffect, useRef } from 'react';
import AvatarCanvas from './components/AvatarCanvas';
import WebSocketStatus from './components/WebSocketStatus';
import ModelUpload from './components/ModelUpload';
import VoiceInput from './components/VoiceInput';
import DebugPanel from './components/DebugPanel';
import ProcessingCards from './components/ProcessingCards';
import AgentStateIndicator from './components/AgentStateIndicator';
import { WebSocketClient } from './logic/WebSocketClient';
import { AvatarStateManager } from './logic/AvatarStateManager';
import './style.css';

const DEFAULT_MODEL_URL = '/models/Mimi.vrm';

export default function App() {
  const [modelUrl, setModelUrl] = useState(null);
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [isObsMode, setIsObsMode] = useState(false);
  const [frameStats, setFrameStats] = useState({ frameCount: 0, fps: 0, lastFrameTime: 0 });

  const wsClientRef = useRef(null);
  const stateManagerRef = useRef(null);
  const viewerRef = useRef(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('mode') === 'obs') {
      setIsObsMode(true);
      document.body.style.background = 'transparent';
    }

    const wsClient = new WebSocketClient('ws://localhost:8765');
    const stateManager = new AvatarStateManager(wsClient);

    wsClientRef.current = wsClient;
    stateManagerRef.current = stateManager;

    const unsubStatus = wsClient.onStatusChange((status) => {
      setWsStatus(status);
      if (status === 'connected') {
        stateManager.isController = true;
      }
    });

    const unsubMessage = wsClient.onMessage((msg) => {
      if (msg.type === 'avatar_control' && viewerRef.current) {
        const exprCtrl = viewerRef.current.expressionController;
        if (!exprCtrl) return;

        if (msg.emotion) {
          exprCtrl.setExpression(msg.emotion);
          stateManager.setExpression(msg.emotion);
        }
        if (msg.speak && msg.speech_text) {
          const duration = msg.speech_text.length * 50;
          exprCtrl.speak(duration);
          stateManager.setSpeaking(true);
          setTimeout(() => stateManager.setSpeaking(false), duration);
        }
      }
    });

    wsClient.connect().catch(err => {
      console.warn('WS Connect info', err);
    });

    return () => {
      unsubStatus();
      unsubMessage();
      wsClient.disconnect();
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setModelUrl(DEFAULT_MODEL_URL);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const handleViewerReady = (viewer) => {
    viewerRef.current = viewer;
    if (viewer && viewer.animationManager) {
      viewer.animationManager.loadAnimation('Idle', '/animations/Idle.fbx')
        .then(() => {
          viewer.animationManager.play('Idle', true);
          if (stateManagerRef.current) stateManagerRef.current.setAnimation('Idle');
          console.log('[App] Idle animation started');
        })
        .catch(e => console.warn('Idle anim missing', e));
    }
  };

  const handleSendMessage = (text) => {
    setLastUserMessage(text);
    if (wsClientRef.current) {
      wsClientRef.current.send({ type: 'chat', text });
    }
  };

  if (isObsMode) {
    return (
      <div className="obs-container">
        <AvatarCanvas
          modelUrl={modelUrl}
          onViewerReady={handleViewerReady}
          wsConnection={wsClientRef.current?.ws}
          wsClient={wsClientRef.current}
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
          <ModelUpload onModelLoaded={setModelUrl} />
          <div className="divider" />
          <VoiceInput wsClient={wsClientRef.current} />
        </aside>

        <section className="viewport-area">
          <div className="avatar-viewport">
            <AvatarCanvas
              modelUrl={modelUrl}
              onViewerReady={handleViewerReady}
              onCameraChange={(cam) => {
                if (stateManagerRef.current && stateManagerRef.current.isController) {
                  stateManagerRef.current.setCamera(cam.position, cam.target);
                }
              }}
              onFrameCaptureUpdate={(stats) => setFrameStats(stats)}
              wsConnection={wsClientRef.current?.ws}
              wsClient={wsClientRef.current}
            />
          </div>
          <ProcessingCards wsClient={wsClientRef.current} />
        </section>

        <aside className="sidebar right-sidebar">
          <h3>Agent State</h3>
          <AgentStateIndicator wsClient={wsClientRef.current} />
          <div className="divider" />
          <DebugPanel wsClient={wsClientRef.current} frameStats={frameStats} />
        </aside>
      </main>
    </div>
  );
}
