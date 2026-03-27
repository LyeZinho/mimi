import React, { useEffect, useRef } from 'react';
import { AvatarViewer } from '../logic/AvatarViewer';

export default function AvatarCanvas({ modelUrl, onViewerReady, onCameraChange, onModelLoaded, wsConnection = null, wsClient = null }) {
  const canvasRef = useRef(null);
  const viewerRef = useRef(null);
  const lastModelUrlRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const viewer = new AvatarViewer(canvasRef.current, null);
    viewerRef.current = viewer;

    console.log('[AvatarCanvas] MONTADO');

    if (onViewerReady) {
      onViewerReady(viewer);
    }

    viewer.onCameraChange = (cameraData) => {
      if (onCameraChange) {
        onCameraChange(cameraData);
      }
    };

    if (wsClient) {
      const startCapture = () => {
        if (wsClient.ws && wsClient.ws.readyState === WebSocket.OPEN && viewerRef.current) {
          viewerRef.current.startFrameCapture(wsClient.ws);
          console.log('[AvatarCanvas] Frame capture started');
        }
      };

      if (wsClient.isConnected()) {
        startCapture();
      } else {
        wsClient.onStatusChange((status) => {
          if (status === 'connected') {
            startCapture();
          } else if (status === 'disconnected') {
            if (viewerRef.current) {
              viewerRef.current.stopFrameCapture();
            }
          }
        });
      }
    }

    const handleResize = () => {
      viewer.onWindowResize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      viewer.stopFrameCapture();
      viewer.dispose();
      viewerRef.current = null;
      console.log('[AvatarCanvas] DESMONTADO');
    };
  }, []);

  useEffect(() => {
    if (modelUrl && viewerRef.current) {
      if (lastModelUrlRef.current === modelUrl) {
        return;
      }
      lastModelUrlRef.current = modelUrl;
      console.log('[AvatarCanvas] Carregando modelo:', modelUrl);
      viewerRef.current.loadVRM(modelUrl).then((vrm) => {
        console.log('[AvatarCanvas] Model loaded in Canvas');
        if (onModelLoaded) {
          onModelLoaded(vrm);
        }
      }).catch(console.error);
    }
  }, [modelUrl, onModelLoaded]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        width: '100%',
        height: '100%',
        display: 'block',
        borderRadius: '8px',
        outline: 'none'
      }}
    />
  );
}
