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

    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )

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
