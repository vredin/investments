from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ADMIN_PASSWORD_HASH: str

    OPENROUTER_API_KEY: str = ""

    FREEDOM_PUBLIC_KEY: str = ""
    FREEDOM_PRIVATE_KEY: str = ""
    FREEDOM_LOGIN: str = ""
    FREEDOM_PASSWORD: str = ""

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    SENTRY_DSN: str = ""
    APP_ENV: str = "production"

    SESSION_MAX_AGE: int = 43200  # 12 hours in seconds

    def __init__(self, **data):
        super().__init__(**data)
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not self.SECRET_KEY:
            raise ValueError("SECRET_KEY is required")


@lru_cache
def get_settings() -> Settings:
    return Settings()
