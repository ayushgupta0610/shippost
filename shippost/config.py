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
    # Commits to use when neither --n nor --since is given. Small = fast prompt.
    default_n: int = Field(default=5)
    # Total budget for diff text across ALL selected commits (chars). Keeps the
    # prompt small so generation stays fast. Newest commits get the budget first.
    max_total_diff_chars: int = Field(default=6000)


settings = Settings()
