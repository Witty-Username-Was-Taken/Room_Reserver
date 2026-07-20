# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    project_name: str
    version: str
    database_url: str
    model_config = SettingsConfigDict(
        env_file=project_root / ".env", env_file_encoding="utf-8"
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
