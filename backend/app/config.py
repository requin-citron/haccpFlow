from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
