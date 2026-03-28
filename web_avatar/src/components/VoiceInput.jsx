import React, { useState, useRef, useEffect } from 'react';

export default function VoiceInput({ wsClient }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState(null);

  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setError(null);

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: !isMuted,
        }
      });

      streamRef.current = stream;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      source.connect(processor);
      processor.connect(audioContext.destination);

      const targetSampleRate = 16000;
      const resampleRatio = audioContext.sampleRate / targetSampleRate;
      let resampleBuffer = [];
      let pcmBuffer = [];
      let chunkCount = 0;

      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);

        for (let i = 0; i < inputData.length; i++) {
          resampleBuffer.push(inputData[i]);

          if (resampleBuffer.length >= resampleRatio) {
            const sample = resampleBuffer.reduce((a, b) => a + b) / resampleBuffer.length;
            const pcm16 = Math.max(-1, Math.min(1, sample)) * 0x7FFF;

            const byte1 = pcm16 & 0xff;
            const byte2 = (pcm16 >> 8) & 0xff;
            
            pcmBuffer.push(byte1, byte2);
            resampleBuffer = [];
          }
        }

        if (pcmBuffer.length >= 1024) {
          if (wsClient && wsClient.isConnected()) {
            const sent = wsClient.send({
              type: 'audio_chunk',
              data: pcmBuffer,
              sample_rate: targetSampleRate,
            });
            if (sent) {
              chunkCount++;
              if (chunkCount % 10 === 0) {
                console.log(`[VoiceInput] Sent ${chunkCount} audio chunks`);
              }
            }
          } else {
            console.warn('[VoiceInput] WebSocket not connected, cannot send audio');
          }
          pcmBuffer = [];
        }
      };

      setIsRecording(true);
      console.log('[VoiceInput] Recording started, WebSocket connected:', wsClient?.isConnected());
    } catch (err) {
      console.error('Microphone access denied:', err);
      setError('Microfone não disponível');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    audioChunksRef.current = [];
    setIsRecording(false);
    console.log('[VoiceInput] Recording stopped');
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  return (
    <div className="voice-input-container">
      <div className="voice-controls">
        <button
          className={`mic-button ${isRecording ? 'recording' : ''}`}
          onClick={toggleRecording}
          title={isRecording ? 'Parar gravação' : 'Iniciar gravação'}
        >
          {isRecording ? '🔴' : '🎤'}
        </button>

        <button
          className={`mute-button ${isMuted ? 'muted' : ''}`}
          onClick={toggleMute}
          title={isMuted ? 'Remover mute' : 'Mutar entrada'}
        >
          {isMuted ? '🔇' : '🔊'}
        </button>
      </div>

      {error && <div className="voice-error">{error}</div>}

      <div className="voice-status">
        {isRecording && <span className="pulse">● Gravando...</span>}
        {!isRecording && !error && <span className="idle">Pronto para falar</span>}
      </div>
    </div>
  );
}
