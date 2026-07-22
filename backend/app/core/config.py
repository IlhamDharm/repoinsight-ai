from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RepoInsight AI API"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:12345678@localhost:5432/repoinsight_ai"
    database_echo: bool = False

    # GitHub Integration
    github_api_url: str = "https://api.github.com"
    github_token: str = ""
    github_timeout: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="REPOINSIGHT_",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
