"""Async OpenAI SDK client pointed at OpenRouter. The only LLM transport."""

from functools import lru_cache

from openai import AsyncOpenAI

from shippost.config import settings


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    # One client per process. In tests, monkeypatch get_client on the consuming
    # module, or call get_client.cache_clear() in fixture teardown.
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to .env before drafting."
        )
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
