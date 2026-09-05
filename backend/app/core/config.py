from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/datastraw"
    openrouter_api_key: str | None = None
    openrouter_model: str = "minimax/minimax-m3:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    frontend_origin: str = "http://localhost:5173"
    similarity_threshold: float = 0.35
    similarity_min_margin: float = 0.02
    similarity_strong_match_threshold: float = 0.55
    # Simple dev auth (seed user stored in env). Use only for local/dev testing.
    auth_user_email: str | None = None
    auth_user_password: str | None = None
    auth_token_secret: str | None = None
    auth_token_ttl_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()