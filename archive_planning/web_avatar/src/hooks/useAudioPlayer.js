import { useState, useRef, useCallback } from 'react';

export const useAudioPlayer = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [bufferedSeconds, setBufferedSeconds] = useState(0);
  const audioContextRef = useRef(null);
  const audioBufferRef = useRef([]);
  const playbackTimeRef = useRef(0);
  const playLoopRef = useRef(null);
  
  const initAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);
  
  const addAudioChunk = useCallback((base64Data, sampleRate = 22050) => {
    try {
      const binaryString = atob(base64Data);
      const byteArray = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        byteArray[i] = binaryString.charCodeAt(i);
      }
      
      const audioContext = initAudioContext();
      const float32Array = new Float32Array(byteArray.length / 2);
      
      const view = new DataView(byteArray.buffer);
      for (let i = 0; i < float32Array.length; i++) {
        float32Array[i] = view.getInt16(i * 2, true) / 32768.0;
      }
      
      audioBufferRef.current.push({
        data: float32Array,
        sampleRate,
      });
      
      const totalSamples = audioBufferRef.current.reduce(
        (sum, chunk) => sum + chunk.data.length, 
        0
      );
      setBufferedSeconds(totalSamples / sampleRate);
      
    } catch (error) {
      console.error('Failed to add audio chunk:', error);
    }
  }, [initAudioContext]);
  
  const startPlayback = useCallback(async () => {
    const audioContext = initAudioContext();
    
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }
    
    setIsPlaying(true);
    playbackTimeRef.current = 0;
    
    playLoopRef.current = (async () => {
      while (isPlaying && audioBufferRef.current.length > 0) {
        const chunk = audioBufferRef.current[0];
        
        const audioBuffer = audioContext.createBuffer(
          1,
          chunk.data.length,
          chunk.sampleRate
        );
        
        audioBuffer.getChannelData(0).set(chunk.data);
        
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioContext.destination);
        
        const playbackDuration = chunk.data.length / chunk.sampleRate;
        source.start(0);
        
        await new Promise(resolve => {
          setTimeout(resolve, playbackDuration * 1000);
        });
        
        audioBufferRef.current.shift();
      }
      
      setIsPlaying(false);
    })();
  }, [isPlaying, initAudioContext]);
  
  const stopPlayback = useCallback(() => {
    setIsPlaying(false);
    audioBufferRef.current = [];
    playbackTimeRef.current = 0;
  }, []);
  
  const clearBuffer = useCallback(() => {
    audioBufferRef.current = [];
    setBufferedSeconds(0);
  }, []);
  
  return {
    isPlaying,
    bufferedSeconds,
    addAudioChunk,
    startPlayback,
    stopPlayback,
    clearBuffer,
  };
};
