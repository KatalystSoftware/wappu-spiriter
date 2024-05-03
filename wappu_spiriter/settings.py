from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    env: Literal["dev", "prod"] = "dev"
    listen: str | None = None
    port: int | None = None
    webhook_path: str = ""
    webhook_url: str | None = None


settings = Settings()
