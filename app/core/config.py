from functools import lru_cache
from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
# Project root: D:\Rexcoder
BASE_DIR = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env."""
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    # Groq model configuration
    GROQ_API_KEY: SecretStr
    GROQ_MODEL: str
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance."""
    return Settings()