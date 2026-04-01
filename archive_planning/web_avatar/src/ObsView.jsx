
import React, { useEffect, useRef, useState } from 'react';
import { WebSocketClient } from './logic/WebSocketClient';
import { AvatarStateManager } from './logic/AvatarStateManager';
import AvatarCanvas from './components/AvatarCanvas';
import WebSocketStatus from './components/WebSocketStatus';

// Utilitário para comparar objetos superficiais
function shallowEqual(objA, objB) {
  if (objA === objB) return true;
  if (!objA || !objB) return false;
  const keysA = Object.keys(objA);
  const keysB = Object.keys(objB);
  if (keysA.length !== keysB.length) return false;
  for (let key of keysA) {
    if (objA[key] !== objB[key]) return false;
  }
  return true;
}

export default function ObsView() {
  const [wsStatus, setWsStatus] = useState('disconnected');
  const [modelUrl, setModelUrl] = useState(null);
  const wsClientRef = useRef(null);
  const stateManagerRef = useRef(null);
  const viewerRef = useRef(null);
  const lastStateRef = useRef({});

  // Aplica o estado recebido no AvatarViewer
  const applyStateToViewer = (state) => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // Modelo
    if (state.model && state.model !== lastStateRef.current.model) {
      setModelUrl(state.model);
      lastStateRef.current.model = state.model;
    }

    // Expressão
    if (
      viewer.expressionController &&
      state.expression &&
      state.expression !== lastStateRef.current.expression
    ) {
      viewer.expressionController.setExpression(state.expression);
    }

    // Animação
    if (
      viewer.animationManager &&
      state.animation &&
      state.animation !== lastStateRef.current.animation
    ) {
      // Suporte a objeto animation { name, url }
      if (typeof state.animation === 'object' && state.animation.name && state.animation.url) {
        viewer.animationManager.loadAnimation(state.animation.name, state.animation.url)
          .then(() => {
            viewer.animationManager.play(state.animation.name, 0.5);
          })
          .catch(e => console.error('Erro ao carregar animação:', e));
      } else if (typeof state.animation === 'string') {
        viewer.animationManager.play(state.animation, 0.5);
      }
    }

    // Câmera
    if (state.camera && !shallowEqual(state.camera, lastStateRef.current.camera)) {
      if (viewer.camera) {
        const { position, target } = state.camera;
        if (position) {
          viewer.camera.position.set(position.x, position.y, position.z);
        }
        if (viewer.controls && target) {
          viewer.controls.target.set(target.x, target.y, target.z);
          viewer.controls.update();
        }
      }
    }

    // Fundo
    if (state.background && state.background !== lastStateRef.current.background) {
      if (viewer.renderer) {
        if (state.background === 'transparent') {
          viewer.renderer.setClearColor(0x000000, 0);
        } else {
          viewer.renderer.setClearColor(state.background);
        }
      }
    }

    lastStateRef.current = { ...state };
  };

  useEffect(() => {
    const wsClient = new WebSocketClient('ws://localhost:8765');
    const stateManager = new AvatarStateManager(wsClient);
    stateManager.setMode(false); // viewer mode
    wsClientRef.current = wsClient;
    stateManagerRef.current = stateManager;

    wsClient.onStatusChange((status) => setWsStatus(status));
    wsClient.onMessage((msg) => {
      if (msg.type === 'state' && msg.state) {
        // Atualiza modelUrl para AvatarCanvas (só para carregar o canvas)
        if (msg.state.model) setModelUrl(msg.state.model);
        // Aplica incrementalmente o estado recebido
        applyStateToViewer(msg.state);
      }
    });
    wsClient.connect().catch(console.error);
    return () => wsClient.disconnect();
    // eslint-disable-next-line
  }, []);

  const handleViewerReady = (viewer) => {
    viewerRef.current = viewer;
    // Fundo transparente para OBS por padrão
    if (viewer && viewer.renderer) {
      viewer.renderer.setClearColor(0x000000, 0);
    }
  };

  return (
    <div style={{width: '100vw', height: '100vh', background: 'transparent', margin: 0, padding: 0, overflow: 'hidden'}}>
      <AvatarCanvas modelUrl={modelUrl} onViewerReady={handleViewerReady} />
    </div>
  );
}
