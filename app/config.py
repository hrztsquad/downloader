"""Modul konfigurasi SUKU-Monitor berbasis pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    secret_key: str = Field(default="dev-secret-key-change-in-prod", alias="SECRET_KEY")

    database_url: str = Field(default="sqlite:///./suku_monitor.db", alias="DATABASE_URL")

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.8-flash", alias="GEMINI_MODEL")

    ig_account_id: str = Field(default="", alias="IG_ACCOUNT_ID")
    ig_access_token: str = Field(default="", alias="IG_ACCESS_TOKEN")

    crawl_interval_minutes: int = Field(default=180, alias="CRAWL_INTERVAL_MINUTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
