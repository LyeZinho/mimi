
import React, { useEffect, useRef } from 'react';
import { AvatarViewer } from '../logic/AvatarViewer';

export default function AvatarCanvas({ modelUrl, onViewerReady, onCameraChange, onModelLoaded }) {
  const canvasRef = useRef(null);
  const viewerRef = useRef(null);
  const lastModelUrlRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    // Initialize Viewer
    const viewer = new AvatarViewer(canvasRef.current);
    viewerRef.current = viewer;

    console.log('[AvatarCanvas] MONTADO');

    if (onViewerReady) {
      onViewerReady(viewer);
    }

    // Bind camera update
    viewer.onCameraChange = (cameraData) => {
      if (onCameraChange) {
        onCameraChange(cameraData);
      }
    };

    const handleResize = () => {
      viewer.onWindowResize();
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      viewer.dispose();
      viewerRef.current = null;
      console.log('[AvatarCanvas] DESMONTADO');
    };
  }, []);

  // Load model when URL changes
  useEffect(() => {
    if (modelUrl && viewerRef.current) {
      if (lastModelUrlRef.current === modelUrl) {
        // Mesmo modelo já carregado, não recarrega
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
