import React, { useEffect, useState, useRef } from 'react';
import styles from './AvatarSync.module.css';

const PHONEME_TO_BLEND_SHAPE = {
  'a': 'A',
  'e': 'E',
  'i': 'I',
  'o': 'O',
  'u': 'U',
  's': 'SS',
  't': 'T',
  'n': 'N',
  'l': 'L',
  'ː': 'U',
};

export const AvatarSync = ({ ws, isConnected, vrm }) => {
  const [currentPhoneme, setCurrentPhoneme] = useState(null);
  const phonemeTimelineRef = useRef([]);
  const currentTimeRef = useRef(0);
  const animationFrameRef = useRef(null);
  
  useEffect(() => {
    if (!ws || !isConnected) return;
    
    const handleMessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        
        if (message.type === 'phoneme_data' || message.phonemes) {
          const sampleRate = message.sample_rate || 22050;
          const timeline = [];
          
          message.phonemes.forEach((phoneme, index) => {
            const startPos = message.sample_positions?.[index] || 0;
            const endPos = message.sample_positions?.[index + 1] || startPos + 2048;
            
            timeline.push({
              phoneme,
              startTime: startPos / sampleRate,
              endTime: endPos / sampleRate,
              duration: (endPos - startPos) / sampleRate,
            });
          });
          
          phonemeTimelineRef.current = timeline;
        } else if (message.type === 'audio_chunk') {
          currentTimeRef.current += (message.audio_bytes || 0) / (22050 * 2);
        } else if (message.type === 'audio_complete') {
          currentTimeRef.current = 0;
          phonemeTimelineRef.current = [];
          setCurrentPhoneme(null);
        }
      } catch (error) {
        console.error('Failed to process phoneme data:', error);
      }
    };
    
    ws.addEventListener('message', handleMessage);
    
    return () => {
      ws.removeEventListener('message', handleMessage);
    };
  }, [ws, isConnected]);
  
  useEffect(() => {
    if (!vrm || phonemeTimelineRef.current.length === 0) return;
    
    const animate = () => {
      const current = phonemeTimelineRef.current.find(
        p => currentTimeRef.current >= p.startTime && currentTimeRef.current < p.endTime
      );
      
      if (current) {
        setCurrentPhoneme(current.phoneme);
        
        const blendShape = PHONEME_TO_BLEND_SHAPE[current.phoneme];
        if (blendShape && vrm.expressionManager) {
          vrm.expressionManager.setValue(blendShape, 1.0);
        }
      } else {
        setCurrentPhoneme(null);
        if (vrm.expressionManager) {
          Object.values(PHONEME_TO_BLEND_SHAPE).forEach(shape => {
            vrm.expressionManager.setValue(shape, 0.0);
          });
        }
      }
      
      animationFrameRef.current = requestAnimationFrame(animate);
    };
    
    animationFrameRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [vrm]);
  
  return (
    <div className={styles['avatar-sync']}>
      <div className={styles['sync-status']}>
        {currentPhoneme ? (
          <span>🎤 Phoneme: <strong>{currentPhoneme}</strong></span>
        ) : (
          <span>🎤 Idle</span>
        )}
        <span>Timeline: {phonemeTimelineRef.current.length} phonemes</span>
        <span>Time: {currentTimeRef.current.toFixed(2)}s</span>
      </div>
    </div>
  );
};

export default AvatarSync;
