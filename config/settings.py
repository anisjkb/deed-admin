# config/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",            # auto-load .env (optional; process env wins)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Sessions / security (cookie for SessionMiddleware)
    SESSION_SECRET: str = "dev-only-please-change"
    SESSION_SAMESITE: str = "lax"      # "lax" | "strict" | "none"
    SESSION_HTTPS_ONLY: bool = True    # True in prod (requires HTTPS)

    # Redis / Flash messaging
    REDIS_URL: str = "redis://localhost:6379/0"
    FLASH_TTL: int = 600               # seconds
    FLASH_PREFIX: str = "flashq:"
    FLASH_MAX: int = 10

settings = Settings()