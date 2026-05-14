"""App configuration via pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://paczkomat:changeme_local_only@localhost:5432/paczkomat_atlas"
    inpost_api_url: str = "https://api-global-points.easypack24.net/v1"
    log_level: str = "INFO"
    # Martin tile-server health probe URL — defaults to the docker-compose
    # service name. Override in .env for non-compose environments.
    martin_health_url: str = "http://martin:3000/health"


settings = Settings()
