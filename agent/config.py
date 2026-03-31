from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b-instruct"
    ollama_sentiment_model: str = "qwen2.5:0.5b"
    redis_url: str = "redis://localhost:6379"
    sqlite_path: str = "data/memory.db"
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8080
    log_level: str = "INFO"

settings = Settings()
