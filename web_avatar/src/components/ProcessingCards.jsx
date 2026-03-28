import React, { useState, useEffect } from 'react';

export default function ProcessingCards({ wsClient = null, lastUserMessage = null }) {
  const [inputText, setInputText] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [response, setResponse] = useState(null);
  const [inputSentiment, setInputSentiment] = useState(null);
  const [responseEmotion, setResponseEmotion] = useState(null);

  useEffect(() => {
    if (lastUserMessage) {
      setInputText(lastUserMessage);
      setProcessing(null);
      setResponse(null);
      setInputSentiment(null);
      setResponseEmotion(null);
    }
  }, [lastUserMessage]);

  useEffect(() => {
    if (!wsClient) return;

    const handleMessage = (msg) => {
      if (msg.type === 'processing_update') {
        const { stage, text, intent, plan, sentiment, emotion } = msg;
        
        if (stage === 'input') {
          setInputText(text);
          setInputSentiment(null);
        }
        
        if (stage === 'input_sentiment') {
          setInputSentiment(sentiment);
        }
        
        if (stage === 'processing') {
          setProcessing({
            intent: intent || 'unknown',
            plan: plan || '',
          });
        }
        
        if (stage === 'response_emotion') {
          setResponseEmotion(emotion);
        }
        
        if (stage === 'response') {
          setResponse(text);
        }
      }
      
      if (msg.type === 'chat_response') {
        setResponse(msg.text);
      }
    };

    const unsub = wsClient.onMessage(handleMessage);
    return () => unsub();
  }, [wsClient]);

  const getSentimentEmoji = (sentiment) => {
    const map = {
      positive: '😊',
      negative: '😔',
      neutral: '😐',
      happy: '😊',
      sad: '😔',
      angry: '😠',
      surprised: '😲',
      confused: '😕',
    };
    return map[sentiment?.toLowerCase()] || '😐';
  };

  const Card = ({ title, content, emoji, color, sentiment }) => (
    <div style={{
      flex: 1,
      background: '#1a1a2e',
      border: `1px solid ${color}`,
      borderRadius: '12px',
      padding: '1rem',
      minWidth: 0,
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '0.75rem',
        color: color,
        fontWeight: 'bold',
        fontSize: '0.85rem',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
      }}>
        <span style={{ fontSize: '1.2rem' }}>{emoji}</span>
        {title}
      </div>
      
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        overflow: 'hidden',
      }}>
        {content ? (
          typeof content === 'string' ? (
            <p style={{
              margin: 0,
              color: '#e5e7eb',
              fontSize: '0.9rem',
              lineHeight: '1.4',
              wordBreak: 'break-word',
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: 3,
              WebkitBoxOrient: 'vertical',
            }}>
              {content}
            </p>
          ) : (
            <div style={{ color: '#e5e7eb', fontSize: '0.85rem' }}>
              {content.intent && (
                <div style={{ marginBottom: '0.5rem' }}>
                  <span style={{ color: '#9ca3af' }}>Intent: </span>
                  <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{content.intent}</span>
                </div>
              )}
              {content.plan && (
                <div>
                  <span style={{ color: '#9ca3af' }}>Plan: </span>
                  <span style={{ color: '#a78bfa' }}>{content.plan}</span>
                </div>
              )}
            </div>
          )
        ) : (
          <span style={{ color: '#6b7280', fontSize: '0.85rem', fontStyle: 'italic' }}>
            Waiting for input...
          </span>
        )}
      </div>
      
      {(sentiment || inputSentiment || responseEmotion) && (
        <div style={{
          marginTop: '0.75rem',
          paddingTop: '0.5rem',
          borderTop: '1px solid #333',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.8rem',
        }}>
          <span style={{ color: '#9ca3af' }}>Sentiment:</span>
          <span style={{ fontSize: '1rem' }}>
            {getSentimentEmoji(sentiment || inputSentiment || responseEmotion)}
          </span>
          <span style={{ color: '#9ca3af', textTransform: 'capitalize' }}>
            {sentiment || inputSentiment || responseEmotion || 'neutral'}
          </span>
        </div>
      )}
    </div>
  );

  return (
    <div style={{
      display: 'flex',
      gap: '1rem',
      padding: '1rem',
      background: '#121218',
      borderTop: '1px solid #333',
    }}>
      <Card 
        title="Input" 
        emoji="🎤"
        color="#22c55e"
        content={inputText}
        sentiment={inputSentiment}
      />
      
      <Card 
        title="Processing" 
        emoji="⚙️"
        color="#f59e0b"
        content={processing}
      />
      
      <Card 
        title="Response" 
        emoji="💬"
        color="#3b82f6"
        content={response}
        sentiment={responseEmotion}
      />
    </div>
  );
}
