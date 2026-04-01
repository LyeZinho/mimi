import React, { useEffect, useState } from 'react';

const BrainDashboard = ({ wsClient }) => {
  const [brains, setBrains] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    if (!wsClient) return;

    const handleBrainStatus = (msg) => {
      if (msg.type === 'brain_status' && msg.brains) {
        setBrains(msg.brains);
        setLastUpdate(new Date(msg.timestamp * 1000).toLocaleTimeString());
      }
    };

    const unsubscribe = wsClient.onMessage(handleBrainStatus);
    return () => unsubscribe();
  }, [wsClient]);

  const getEmoji = (brain) => {
    if (!brain.is_alive) return '⚫';
    if (!brain.is_healthy) return '🔴';
    return '🟢';
  };

  const getStatusText = (brain) => {
    if (!brain.is_alive) return 'stopped';
    if (!brain.is_healthy) return 'unhealthy';
    return 'healthy';
  };

  const brainOrder = [
    'input_brain',
    'reasoning_brain',
    'planning_brain',
    'execution_brain',
    'sentiment_brain',
    'avatar_brain',
    'output_brain',
  ];

  const sortedBrains = [...brains].sort(
    (a, b) => brainOrder.indexOf(a.brain_id) - brainOrder.indexOf(b.brain_id)
  );

  const formatBrainName = (brainId) => {
    return brainId
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>🧠 Brain Activity</h3>
        {lastUpdate && <span style={styles.timestamp}>{lastUpdate}</span>}
      </div>

      <div style={styles.brainsList}>
        {sortedBrains.length === 0 ? (
          <div style={styles.empty}>Waiting for brain status...</div>
        ) : (
          sortedBrains.map((brain) => (
            <div key={brain.brain_id} style={styles.brainItem}>
              <div style={styles.brainHeader}>
                <span style={styles.emoji}>{getEmoji(brain)}</span>
                <span style={styles.brainName}>{formatBrainName(brain.brain_id)}</span>
                <span style={styles.status}>{getStatusText(brain)}</span>
              </div>

              <div style={styles.metrics}>
                <div style={styles.metric}>
                  <span style={styles.metricLabel}>Events:</span>
                  <span style={styles.metricValue}>{brain.events_processed}</span>
                </div>
                <div style={styles.metric}>
                  <span style={styles.metricLabel}>Latency:</span>
                  <span style={styles.metricValue}>{brain.avg_latency_ms.toFixed(1)}ms</span>
                </div>
                <div style={styles.metric}>
                  <span style={styles.metricLabel}>Errors:</span>
                  <span style={styles.metricValue}>{brain.errors}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    backgroundColor: '#1a1a2e',
    borderRadius: '8px',
    padding: '12px',
    color: '#e0e0e0',
    fontFamily: 'monospace',
    fontSize: '12px',
    border: '1px solid #0f3460',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
    paddingBottom: '8px',
    borderBottom: '1px solid #0f3460',
  },
  title: {
    margin: 0,
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#00d4ff',
  },
  timestamp: {
    fontSize: '10px',
    color: '#888',
  },
  brainsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  empty: {
    textAlign: 'center',
    color: '#666',
    padding: '20px 0',
    fontSize: '11px',
  },
  brainItem: {
    backgroundColor: '#16213e',
    borderRadius: '4px',
    padding: '8px',
    border: '1px solid #0f3460',
  },
  brainHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  emoji: {
    fontSize: '16px',
    minWidth: '20px',
  },
  brainName: {
    flex: 1,
    fontWeight: 'bold',
    color: '#00d4ff',
  },
  status: {
    fontSize: '10px',
    color: '#888',
    backgroundColor: '#0a1929',
    padding: '2px 6px',
    borderRadius: '2px',
  },
  metrics: {
    display: 'flex',
    gap: '12px',
    fontSize: '10px',
  },
  metric: {
    display: 'flex',
    gap: '4px',
  },
  metricLabel: {
    color: '#888',
  },
  metricValue: {
    color: '#00d4ff',
    fontWeight: 'bold',
  },
};

export default BrainDashboard;
