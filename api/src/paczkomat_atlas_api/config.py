"""App configuration via pydantic-settings."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://paczkomat:changeme_local_only@localhost:5432/paczkomat_atlas"
    inpost_api_url: str = "https://api-global-points.easypack24.net/v1"
    log_level: str = "INFO"
    # Martin tile-server health probe URL — defaults to the docker-compose
    # service name. Override in .env for non-compose environments.
    martin_health_url: str = "http://martin:3000/health"

    # Comma-separated list of allowed CORS origins. Dev default permits the
    # Next.js dev server only. Production MUST set this explicitly to the
    # public hostname; "*" is rejected by the validator below.
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


settings = Settings()
