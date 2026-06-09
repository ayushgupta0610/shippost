"""Application configuration. The only module that reads the environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str | None = Field(default=None)
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    default_model: str = Field(default="deepseek/deepseek-v4-flash")
    default_tone: str = Field(default="technical")
    max_diff_chars: int = Field(default=4000)


settings = Settings()
