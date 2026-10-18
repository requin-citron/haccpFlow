from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

API_V1_PREFIX = "/api/v1"


class Settings(BaseSettings):
    """Runtime configuration, read from the environment (and an optional .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "info"
    docs_enabled: bool = True
    # Optional absolute URL used to fill the OpenAPI `servers` entry.
    public_api_url: str = ""

    secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    # Comma-separated list of allowed browser origins.
    cors_origins: str = "http://localhost:3000"

    database_url: str

    # Uploaded LaTeX templates are stored as plain files; the database keeps
    # their metadata. Both values are configurable per installation.
    template_max_upload_bytes: int = Field(default=262_144, ge=1_024)
    template_storage_dir: Path = Path("data/templates")
    template_document_storage_dir: Path = Path("data/documents")
    template_pdf_timeout_seconds: int = Field(default=30, ge=5, le=300)
    template_pdf_max_output_bytes: int = Field(default=20 * 1024 * 1024, ge=1_024)
    template_pdf_concurrency: int = Field(default=2, ge=1, le=16)
    template_image_max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1_024)

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: SecretStr = SecretStr("")
    mqtt_client_id: str = "haccpflow-backend"
    mqtt_topic_prefix: str = "zigbee2mqtt"

    # When both are set, the first admin user is created on startup if the
    # users table is empty.
    admin_email: str = ""
    admin_password: SecretStr = SecretStr("")

    # Fallback thresholds in Celsius, used when a new piece of equipment does
    # not provide its own. Override them from the environment.
    default_fridge_min_temperature_c: float = 0.0
    default_fridge_max_temperature_c: float = 4.0
    default_freezer_min_temperature_c: float = -25.0
    default_freezer_max_temperature_c: float = -18.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
