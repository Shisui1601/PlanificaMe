# backend/app/config.py
import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Database - use PostgreSQL if DATABASE_URL is set, otherwise SQLite for dev
    DATABASE_URL: str = "sqlite:///./planificame.db"  # Default para desarrollo local

    # Redis and Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Email — Brevo HTTP API
    BREVO_API_KEY: str = ""
    SMTP_SERVER: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SENDER_EMAIL: str = ""
    SENDER_NAME: str = "PlanificaMe"

    # Frontend / CORS
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8000", "*"]

    # App
    APP_NAME: str = "PlanificaMe API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True


    model_config = SettingsConfigDict(
        env_file=_env_path,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Post-init opcional para derivar valores si están vacíos
    def __init__(self, **values):
        super().__init__(**values)
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL
        if not self.SENDER_EMAIL:
            self.SENDER_EMAIL = self.SMTP_USER

settings = Settings()