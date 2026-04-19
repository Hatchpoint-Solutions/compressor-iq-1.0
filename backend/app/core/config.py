"""Application configuration loaded from environment with sensible defaults."""

import logging
import sys

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Override via environment variables or a ``.env`` file."""

    APP_NAME: str = "CompressorIQ"
    VERSION: str = "0.2.0"

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/compressoriq"
    UPLOAD_DIR: str = "data/uploads"

    # Default source directory for file discovery (project root)
    SOURCE_DATA_DIR: str = ""

    LOG_LEVEL: str = "INFO"

    # OpenAI LLM settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2000

    @property
    def llm_enabled(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def health_alert_work_order_severity_set(self) -> set[str]:
        return {
            x.strip().lower()
            for x in self.HEALTH_ALERT_WORK_ORDER_SEVERITIES.split(",")
            if x.strip()
        }

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
    )

    # Optional API key — when non-empty, mutating endpoints require X-API-Key or Bearer token
    API_KEY: str = ""

    # Auto-create system work orders from health assessment alerts (high/critical by default)
    AUTO_WORK_ORDERS_FROM_HEALTH_ALERTS: bool = True
    HEALTH_ALERT_WORK_ORDER_SEVERITIES: str = "high,critical"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()


def configure_logging() -> None:
    """Set up structured logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
