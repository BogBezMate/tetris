from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/tetris"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 480
    jira_sample_file: str = "../response_example.json"
    jira_base_url: str = "https://jira.askona.ru"
    jira_token: str = ""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def jira_sample_path(self) -> Path:
        p = Path(self.jira_sample_file)
        return p if p.is_absolute() else (BACKEND_DIR / p).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
