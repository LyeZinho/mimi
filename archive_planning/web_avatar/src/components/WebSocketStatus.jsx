import React from 'react';

export default function WebSocketStatus({ status }) {
  const color = status === 'connected' ? '#10b981' : status === 'connecting' ? '#f59e42' : '#ef4444';
  const text = status === 'connected' ? 'Conectado' : status === 'connecting' ? 'Conectando...' : 'Desconectado';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: 12, height: 12, borderRadius: '50%', background: color, display: 'inline-block' }} />
      <span style={{ color }}>{text}</span>
    </div>
  );
}
