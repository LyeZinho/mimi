import React, { useState, useEffect, useRef } from 'react';

const EMOTION_COLORS = {
  happy: '#22c55e',
  sad: '#3b82f6',
  angry: '#ef4444',
  surprised: '#f59e0b',
  confused: '#8b5cf6',
  neutral: '#9ca3af',
  thinking: '#6b7280',
};

const MAX_HISTORY = 20;

export default function DebugPanel({ wsClient = null, frameStats = { fps: 0, frameCount: 0 } }) {
  const [emotionHistory, setEmotionHistory] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [currentGesture, setCurrentGesture] = useState(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!wsClient) return;

    const handleMessage = (msg) => {
      if (msg.type === 'avatar_control') {
        const now = new Date().toLocaleTimeString();
        setLastUpdate(now);

        if (msg.emotion) {
          const em = msg.emotion.toLowerCase();
          setCurrentEmotion(em);
          setEmotionHistory(prev => {
            const next = [...prev, { emotion: em, time: Date.now() }];
            return next.slice(-MAX_HISTORY);
          });
        }
        if (msg.gesture) {
          setCurrentGesture(msg.gesture);
        }
      }
    };

    const unsub = wsClient.onMessage(handleMessage);
    return () => unsub();
  }, [wsClient]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    if (emotionHistory.length < 2) {
      ctx.fillStyle = '#333';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Waiting for data...', w / 2, h / 2);
      return;
    }

    const barWidth = Math.max(4, (w - 4) / MAX_HISTORY);

    emotionHistory.forEach((entry, i) => {
      const color = EMOTION_COLORS[entry.emotion] || EMOTION_COLORS.neutral;
      const x = i * barWidth + 2;

      ctx.fillStyle = color;
      ctx.globalAlpha = 0.3 + (i / emotionHistory.length) * 0.7;
      ctx.fillRect(x, 2, barWidth - 1, h - 4);
      ctx.globalAlpha = 1;
    });
  }, [emotionHistory]);

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <span className="debug-title">Activity Monitor</span>
        <span className="debug-time">{lastUpdate || '—'}</span>
      </div>

      <canvas
        ref={canvasRef}
        width={240}
        height={32}
        className="emotion-timeline"
      />

      <div className="debug-metrics">
        <div className="debug-metric">
          <span className="debug-metric-label">Mirror</span>
          <span className="debug-metric-value" style={{ color: '#34d399' }}>
            {frameStats.fps} fps
          </span>
        </div>
        <div className="debug-metric">
          <span className="debug-metric-label">Frames</span>
          <span className="debug-metric-value" style={{ color: '#a78bfa' }}>
            {frameStats.frameCount}
          </span>
        </div>
        <div className="debug-metric">
          <span className="debug-metric-label">Mood</span>
          <span className="debug-metric-value" style={{ color: EMOTION_COLORS[currentEmotion] }}>
            {currentEmotion}
          </span>
        </div>
        <div className="debug-metric">
          <span className="debug-metric-label">Gesture</span>
          <span className="debug-metric-value" style={{ color: '#60a5fa' }}>
            {currentGesture || '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
