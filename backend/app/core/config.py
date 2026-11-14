from functools import lru_cache

from pydantic import field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./storedash.db"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if not isinstance(value, str):
            return value

        if value.startswith("postgres://"):
            return (
                "postgresql+psycopg://"
                + value[len("postgres://"):]
            )

        if value.startswith("postgresql://"):
            return (
                "postgresql+psycopg://"
                + value[len("postgresql://"):]
            )

        return value

    cors_origins: str = "http://localhost:3000"

    operating_timezone: str = "Africa/Accra"

    operating_cutoff_hour: int = 18

    # Keep false while developing.
    # Change to true when StoreDash goes live.
    enforce_operating_hours: bool = False

    # Hubtel payments / payouts
    hubtel_enabled: bool = False
    hubtel_api_id: str = ""
    hubtel_api_key: str = ""
    hubtel_collection_account: str = ""
    hubtel_disbursement_account: str = ""
    hubtel_callback_base_url: str = "http://127.0.0.1:8000"
    hubtel_receive_base_url: str = "https://rmp.hubtel.com"
    hubtel_send_base_url: str = "https://smp.hubtel.com"
    hubtel_status_base_url: str = "https://api-txnstatus.hubtel.com"
    hubtel_verification_base_url: str = "https://rnv.hubtel.com"

    # Dedicated StoreDash payment-phone relay.
    sms_relay_enabled: bool = False
    sms_relay_key: str = ""
    sms_relay_allowed_senders: str = ""
    hubtel_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.cors_origins.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
