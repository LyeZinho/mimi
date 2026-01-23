import React from 'react';

const EXPRESSIONS = [
  { key: 'neutral', label: 'Neutro' },
  { key: 'happy', label: 'Feliz' },
  { key: 'sad', label: 'Triste' },
  { key: 'angry', label: 'Bravo' },
  { key: 'surprised', label: 'Surpreso' },
  { key: 'relaxed', label: 'Relaxado' },
];

export default function ExpressionControls({ onExpressionChange }) {
  return (
    <div style={{ margin: '1rem 0' }}>
      <label style={{ fontWeight: 600 }}>Expressão:</label>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
        {EXPRESSIONS.map((exp) => (
          <button
            key={exp.key}
            onClick={() => onExpressionChange && onExpressionChange(exp.key)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 8,
              border: '1px solid #333',
              background: '#222',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            {exp.label}
          </button>
        ))}
      </div>
    </div>
  );
}
