from shippost.config import Settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)  # type: ignore[call-arg]  # ignore any real .env
    assert s.default_model == "deepseek/deepseek-v4-flash"
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert s.default_tone == "technical"
    assert s.default_n == 5
    assert s.max_total_diff_chars == 6000


def test_api_key_optional_at_construction():
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.openrouter_api_key is None


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("DEFAULT_MODEL", "openai/gpt-5")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.openrouter_api_key == "sk-test"
    assert s.default_model == "openai/gpt-5"
