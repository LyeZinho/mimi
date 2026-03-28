import React, { useState, useEffect } from 'react';

const EMOTION_MAP = {
  happy: { emoji: '😊', color: '#22c55e', label: 'Happy' },
  sad: { emoji: '😢', color: '#3b82f6', label: 'Sad' },
  angry: { emoji: '😠', color: '#ef4444', label: 'Angry' },
  surprised: { emoji: '😲', color: '#f59e0b', label: 'Surprised' },
  confused: { emoji: '😕', color: '#8b5cf6', label: 'Confused' },
  neutral: { emoji: '😐', color: '#9ca3af', label: 'Neutral' },
  thinking: { emoji: '🤔', color: '#6b7280', label: 'Thinking' },
};

const GESTURE_LIST = ['wave', 'nod', 'shake', 'point', 'shrug', 'bow'];
const ANIMATION_LIST = ['Idle', 'Walk', 'Dance', 'Talk'];
const EXPRESSION_LIST = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'relaxed'];

export default function AgentStateIndicator({ wsClient = null }) {
  const [emotion, setEmotion] = useState('neutral');
  const [gesture, setGesture] = useState(null);
  const [animation, setAnimation] = useState('Idle');
  const [speaking, setSpeaking] = useState(false);
  const [expression, setExpression] = useState('neutral');

  useEffect(() => {
    if (!wsClient) return;

    const handleMessage = (msg) => {
      if (msg.type === 'avatar_control') {
        if (msg.emotion) setEmotion(msg.emotion.toLowerCase());
        if (msg.gesture) setGesture(msg.gesture);
        if (msg.speak !== undefined) setSpeaking(msg.speak);
        if (msg.animation) setAnimation(msg.animation);
        if (msg.expression) setExpression(msg.expression);
      }
      if (msg.type === 'set_expression') {
        setExpression(msg.expression);
      }
      if (msg.type === 'set_speaking') {
        setSpeaking(msg.speaking);
      }
    };

    const unsub = wsClient.onMessage(handleMessage);
    return () => unsub();
  }, [wsClient]);

  const emotionInfo = EMOTION_MAP[emotion] || EMOTION_MAP.neutral;

  return (
    <div className="agent-state-indicator">
      <div className="mood-indicator">
        <div className={`mood-face ${emotion}`}>
          {emotionInfo.emoji}
        </div>
        <div className="mood-details">
          <div className="mood-label">Current Mood</div>
          <div className="mood-value" style={{ color: emotionInfo.color }}>
            {emotionInfo.label}
          </div>
        </div>
      </div>

      <div className={`speaking-indicator ${speaking ? 'speaking' : ''}`}>
        <div className="speaking-dot" />
        <span style={{ fontSize: '0.8rem', color: speaking ? '#22c55e' : '#6b7280' }}>
          {speaking ? 'Speaking...' : 'Silent'}
        </span>
      </div>

      <div className="state-group">
        <div className="state-group-label">Gesture</div>
        <div className="pill-bar">
          {GESTURE_LIST.map(g => (
            <span key={g} className={`pill ${gesture === g ? 'active' : ''}`}>
              {g}
            </span>
          ))}
        </div>
      </div>

      <div className="state-group">
        <div className="state-group-label">Animation</div>
        <div className="pill-bar">
          {ANIMATION_LIST.map(a => (
            <span key={a} className={`pill ${animation === a ? 'active' : ''}`}>
              {a}
            </span>
          ))}
        </div>
      </div>

      <div className="state-group">
        <div className="state-group-label">Expression</div>
        <div className="pill-bar">
          {EXPRESSION_LIST.map(e => (
            <span key={e} className={`pill ${expression === e ? 'active' : ''}`}>
              {e}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
