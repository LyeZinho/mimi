"""
Configuration for 7-brain architecture

Customize these settings per environment
"""

# Audio configuration
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "bits_per_sample": 16,
    "frame_duration_ms": 20,
}

# Buffer configuration
BUFFER_CONFIG = {
    "ring_buffer_duration_sec": 3.0,  # 3 seconds of history
    "ring_buffer_channels": 1,
    "chunk_queue_max_size": 100,
    "chunk_ttl_ms": 5000,  # Drop chunks after 5 seconds
}

# Event bus configuration
EVENT_BUS_CONFIG = {
    "max_queue_size": 1000,
    "enable_history": True,
    "max_history": 1000,
}

# Brain configuration
BRAIN_CONFIG = {
    "heartbeat_interval": 1.0,  # seconds
    "health_check_timeout": 5.0,  # seconds before brain considered unhealthy
}

# LLM configuration
LLM_CONFIG = {
    "model": "phi3:mini",
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": True,  # Enable streaming
}

# TTS configuration
TTS_CONFIG = {
    "engine": "piper",  # or "coqui"
    "language": "pt-PT",
    "voice": "mimi_default",
    "speed": 1.0,
}

# Avatar configuration
AVATAR_CONFIG = {
    "model_path": "vroid_model/Mimi.vrm",
    "animation_speed": 1.0,
    "lip_sync_enabled": True,
}

# Orchestrator configuration
ORCHESTRATOR_CONFIG = {
    "user_id": "default_user",
    "log_level": "INFO",
    "metrics_enabled": True,
}

# Sentiment analysis lexicon
SENTIMENT_LEXICON = {
    "positive": [
        "bom", "ótimo", "excelente", "feliz", "adorar", "amar",
        "sim", "legal", "bacana", "incrível", "maravilhoso"
    ],
    "negative": [
        "ruim", "péssimo", "horrível", "triste", "odiar", "não",
        "nunca", "terrível", "chato", "frustrado", "decepcionante"
    ],
}

# Emotion to avatar animation mapping
EMOTION_TO_ANIMATION = {
    "happy": {
        "facial_expression": "smile",
        "intensity": 1.0,
        "duration_ms": 500,
    },
    "sad": {
        "facial_expression": "frown",
        "intensity": 0.8,
        "duration_ms": 500,
    },
    "neutral": {
        "facial_expression": "neutral",
        "intensity": 0.0,
        "duration_ms": 0,
    },
    "angry": {
        "facial_expression": "angry",
        "intensity": 0.9,
        "duration_ms": 500,
    },
    "surprised": {
        "facial_expression": "surprised",
        "intensity": 0.7,
        "duration_ms": 300,
    },
}
