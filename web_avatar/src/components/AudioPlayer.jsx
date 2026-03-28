import React, { useEffect, useState } from 'react';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import styles from './AudioPlayer.module.css';

export const AudioPlayer = ({ ws, isConnected }) => {
  const {
    isPlaying,
    bufferedSeconds,
    addAudioChunk,
    startPlayback,
    stopPlayback,
    clearBuffer,
  } = useAudioPlayer();
  
  const [chunkCount, setChunkCount] = useState(0);
  const [isResponseComplete, setIsResponseComplete] = useState(false);
  
  useEffect(() => {
    if (!ws || !isConnected) return;
    
    const handleMessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'audio_chunk') {
          addAudioChunk(message.audio_data, message.sample_rate || 22050);
          setChunkCount(prev => prev + 1);
          
          if (!isPlaying && chunkCount === 0) {
            startPlayback();
          }
        } else if (message.type === 'audio_complete') {
          setIsResponseComplete(true);
        } else if (message.type === 'processing_update') {
          if (message.stage === 'response_ready') {
            clearBuffer();
            setChunkCount(0);
            setIsResponseComplete(false);
          }
        }
      } catch (error) {
        console.error('Failed to process WebSocket message:', error);
      }
    };
    
    ws.addEventListener('message', handleMessage);
    
    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [ws, isConnected, isPlaying, chunkCount, addAudioChunk, startPlayback, clearBuffer]);
  
  return (
    <div className={styles['audio-player']}>
      <div className={styles['audio-status']}>
        <span>🎵 Audio: {isPlaying ? '▶️ Playing' : chunkCount > 0 ? '⏸️ Buffered' : '⏹️ Idle'}</span>
        <span>Chunks: {chunkCount}</span>
        <span>Buffered: {bufferedSeconds.toFixed(1)}s</span>
        {isResponseComplete && <span>✓ Complete</span>}
      </div>
      
      <div className={styles['audio-controls']}>
        {chunkCount > 0 && !isPlaying && (
          <button onClick={startPlayback}>Play</button>
        )}
        {isPlaying && (
          <button onClick={stopPlayback}>Stop</button>
        )}
        {chunkCount > 0 && (
          <button onClick={clearBuffer}>Clear</button>
        )}
      </div>
    </div>
  );
};

export default AudioPlayer;
