from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./storedash.db"

    cors_origins: str = "http://localhost:3000"

    operating_timezone: str = "Africa/Accra"

    operating_cutoff_hour: int = 18

    # Keep false while developing.
    # Change to true when StoreDash goes live.
    enforce_operating_hours: bool = False

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
