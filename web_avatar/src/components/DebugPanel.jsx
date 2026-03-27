import React, { useState, useEffect, useRef } from 'react';

export default function DebugPanel({ wsClient = null, frameStats = { fps: 0, frameCount: 0 } }) {
  const [emotion, setEmotion] = useState(null);
  const [action, setAction] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [animation, setAnimation] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    if (!wsClient) return;

    const handleMessage = (msg) => {
      if (msg.type === 'avatar_control') {
        if (msg.emotion !== undefined) {
          setEmotion(msg.emotion);
          setLastUpdate(new Date().toLocaleTimeString());
        }
        if (msg.gesture !== undefined) {
          setAction(msg.gesture);
          setLastUpdate(new Date().toLocaleTimeString());
        }
        if (msg.speak !== undefined) {
          setSpeaking(msg.speak);
          setLastUpdate(new Date().toLocaleTimeString());
        }
        if (msg.animation !== undefined) {
          setAnimation(msg.animation);
          setLastUpdate(new Date().toLocaleTimeString());
        }
      }
    };

    wsClient.onMessage(handleMessage);

    return () => {
      if (wsClient && wsClient.onMessage) {
        wsClient.onMessage(null);
      }
    };
  }, [wsClient]);

  const getEmotionColor = (emotion) => {
    const colors = {
      happy: '#22c55e',
      sad: '#3b82f6',
      angry: '#ef4444',
      surprised: '#f59e0b',
      confused: '#8b5cf6',
      neutral: '#9ca3af',
      thinking: '#6b7280'
    };
    return colors[emotion?.toLowerCase()] || '#9ca3af';
  };

  return (
    <div style={{
      padding: '1rem',
      background: '#1a1a2e',
      border: '1px solid #333',
      borderRadius: '8px',
      fontFamily: 'monospace',
      fontSize: '12px',
      color: '#e5e7eb',
      marginTop: '1rem'
    }}>
      <h4 style={{ 
        margin: '0 0 1rem 0', 
        color: '#22c55e',
        fontSize: '14px',
        fontWeight: 'bold'
      }}>
        🔍 Multimodal Debug
      </h4>

      <div style={{ marginBottom: '0.5rem' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '0.5rem',
          alignItems: 'center'
        }}>
          <span style={{ color: '#9ca3af' }}>Emotion:</span>
          <span style={{
            color: getEmotionColor(emotion),
            fontWeight: 'bold',
            textTransform: 'uppercase',
            fontSize: '12px'
          }}>
            {emotion || '—'}
          </span>
        </div>

        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '0.5rem',
          alignItems: 'center'
        }}>
          <span style={{ color: '#9ca3af' }}>Action/Gesture:</span>
          <span style={{ 
            color: '#60a5fa', 
            fontWeight: 'bold',
            fontSize: '12px'
          }}>
            {action || '—'}
          </span>
        </div>

        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '0.5rem',
          alignItems: 'center'
        }}>
          <span style={{ color: '#9ca3af' }}>Speaking:</span>
          <span style={{
            color: speaking ? '#22c55e' : '#9ca3af',
            fontWeight: 'bold',
            fontSize: '12px'
          }}>
            {speaking ? '🔊 ON' : '🔇 OFF'}
          </span>
        </div>

        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: '0.5rem',
          alignItems: 'center'
        }}>
          <span style={{ color: '#9ca3af' }}>Animation:</span>
          <span style={{ 
            color: '#fbbf24',
            fontSize: '12px'
          }}>
            {animation || '—'}
          </span>
        </div>

        <div style={{ 
          borderTop: '1px solid #333',
          paddingTop: '0.5rem',
          marginTop: '0.5rem'
        }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginBottom: '0.5rem',
            alignItems: 'center'
          }}>
            <span style={{ color: '#9ca3af' }}>Mirror FPS:</span>
            <span style={{ 
              color: '#34d399',
              fontWeight: 'bold',
              fontSize: '12px'
            }}>
              {frameStats.fps}
            </span>
          </div>

          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginBottom: '0.5rem',
            alignItems: 'center'
          }}>
            <span style={{ color: '#9ca3af' }}>Frames:</span>
            <span style={{ 
              color: '#a78bfa',
              fontSize: '12px'
            }}>
              {frameStats.frameCount}
            </span>
          </div>
        </div>

        <div style={{
          borderTop: '1px solid #333',
          paddingTop: '0.5rem',
          marginTop: '0.5rem',
          fontSize: '10px',
          color: '#6b7280',
          textAlign: 'right'
        }}>
          Last: {lastUpdate || '—'}
        </div>
      </div>
    </div>
  );
}
