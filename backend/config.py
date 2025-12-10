"""
MELCO-Care Backend Configuration
Centralized configuration management using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # Ollama Settings
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_primary_model: str = Field(default="qwen3:4b", alias="OLLAMA_PRIMARY_MODEL")
    ollama_vision_model: str = Field(default="qwen3:4b", alias="OLLAMA_VISION_MODEL")
    ollama_fallback_model: str = Field(default="gemma3:4b", alias="OLLAMA_FALLBACK_MODEL")
    
    # Database Settings
    database_url: str = Field(default="sqlite:///./database/melco_care.db", alias="DATABASE_URL")
    
    # Model Parameters
    llm_temperature: float = Field(default=0.7)
    llm_max_tokens: int = Field(default=2048)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
