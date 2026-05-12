"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ───── App ─────
    APP_NAME: str = "Civil Monitoring Platform"
    APP_ENV: str = "development"  # development | staging | production
    APP_DEBUG: bool = False
    APP_TIMEZONE: str = "Asia/Seoul"
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ───── Security ─────
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    JWT_ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12

    # ───── CORS ─────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # ───── Database ─────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "civil_monitoring"
    POSTGRES_USER: str = "civil"
    POSTGRES_PASSWORD: str = "civil"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        # Used by Alembic
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ───── Redis ─────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ───── MQTT ─────
    MQTT_HOST: str = "mosquitto"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = "ingest"
    MQTT_PASSWORD: Optional[str] = "ingest_pass"
    MQTT_CLIENT_ID: str = "civil-ingestion-1"
    MQTT_TOPIC_DATA: str = "sites/+/sensors/+/data"
    MQTT_TOPIC_HEARTBEAT: str = "sites/+/devices/+/heartbeat"
    MQTT_KEEPALIVE: int = 60
    MQTT_QOS: int = 1

    # ───── Modbus polling ─────
    # Auto-poll runs hourly by default; set to other cron expression to override
    MODBUS_POLL_CRON: str = "0 * * * *"  # every hour at minute 0
    MODBUS_TIMEOUT_SECONDS: int = 5
    MODBUS_RETRIES: int = 2

    # ───── Hourly export ─────
    HOURLY_EXPORT_ENABLED: bool = True
    HOURLY_EXPORT_CRON: str = "5 * * * *"  # every hour at minute 5
    EXPORT_DIR: str = "/data/exports"

    # ───── Health check ─────
    HEALTH_CHECK_CRON: str = "*/5 * * * *"  # every 5 minutes
    DEVICE_OFFLINE_THRESHOLD_MINUTES: int = 15

    # ───── Email (SMTP) ─────
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = "alerts@civil-monitoring.local"
    SMTP_USE_TLS: bool = True

    # ───── Webhook (Slack/Discord) ─────
    SLACK_WEBHOOK_URL: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None

    # ───── Logging ─────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
