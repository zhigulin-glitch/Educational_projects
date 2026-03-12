from pathlib import Path
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    external_api_url: str = Field(default="https://httpbin.org/post", alias="EXTERNAL_API_URL")
    external_api_timeout: int = Field(default=10, alias="EXTERNAL_API_TIMEOUT")
    db_path: str = Field(default="bot.db", alias="DB_PATH")

    @property
    def admin_ids(self) -> List[int]:
        if not self.admin_ids_raw.strip():
            return []
        return [int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip()]

    @field_validator("bot_token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        if ":" not in value:
            raise ValueError("BOT_TOKEN выглядит некорректно")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()