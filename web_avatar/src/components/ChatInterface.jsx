import React, { useState, useEffect, useRef } from 'react';

export default function ChatInterface({ onSendMessage, messages = [] }) {
    const [inputText, setInputText] = useState('');
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);
    const chatEndRef = useRef(null);

    useEffect(() => {
        // Scroll to bottom
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        // Setup Speech Recognition
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'pt-BR'; // Default to Portuguese as per user language

            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                setInputText(text);
                if (onSendMessage) {
                    onSendMessage(text);
                    setInputText('');
                }
                setIsListening(false);
            };

            recognition.onerror = (event) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
            };

            recognition.onend = () => {
                setIsListening(false);
            };

            recognitionRef.current = recognition;
        }
    }, [onSendMessage]);

    const toggleListening = () => {
        if (!recognitionRef.current) {
            alert("Browser does not support Speech Recognition");
            return;
        }

        if (isListening) {
            recognitionRef.current.stop();
        } else {
            recognitionRef.current.start();
            setIsListening(true);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (inputText.trim()) {
            onSendMessage(inputText);
            setInputText('');
        }
    };

    return (
        <div className="chat-interface" style={{
            display: 'flex',
            flexDirection: 'column',
            height: '300px',
            border: '1px solid #333',
            borderRadius: '8px',
            background: '#1a1a1a',
            marginTop: '1rem'
        }}>
            <div className="chat-history" style={{
                flex: 1,
                overflowY: 'auto',
                padding: '1rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem'
            }}>
                {messages.map((msg, idx) => (
                    <div key={idx} style={{
                        alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                        background: msg.sender === 'user' ? '#007bff' : '#333',
                        color: '#fff',
                        padding: '0.5rem 1rem',
                        borderRadius: '1rem',
                        maxWidth: '80%'
                    }}>
                        <small style={{ display: 'block', fontSize: '0.7em', opacity: 0.7, marginBottom: '2px' }}>
                            {msg.sender === 'user' ? 'Você' : 'Mimi'}
                        </small>
                        {msg.text}
                    </div>
                ))}
                <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSubmit} style={{
                display: 'flex',
                padding: '0.5rem',
                borderTop: '1px solid #333',
                gap: '0.5rem'
            }}>
                <button
                    type="button"
                    onClick={toggleListening}
                    style={{
                        background: isListening ? '#ff4444' : '#444',
                        border: 'none',
                        borderRadius: '50%',
                        width: '40px',
                        height: '40px',
                        cursor: 'pointer',
                        color: 'white',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}
                    title="Microfone"
                >
                    {isListening ? '⏹️' : '🎤'}
                </button>
                <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Digite sua mensagem..."
                    style={{
                        flex: 1,
                        padding: '0.5rem',
                        borderRadius: '20px',
                        border: '1px solid #444',
                        background: '#222',
                        color: 'white'
                    }}
                />
                <button
                    type="submit"
                    style={{
                        background: '#007bff',
                        border: 'none',
                        borderRadius: '20px',
                        padding: '0 1.5rem',
                        color: 'white',
                        cursor: 'pointer'
                    }}
                >
                    Enviar
                </button>
            </form>
        </div>
    );
}
