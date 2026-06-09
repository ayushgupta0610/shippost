import pytest

from shippost.llm import client as client_mod


def test_get_client_raises_without_key(monkeypatch):
    monkeypatch.setattr(client_mod.settings, "openrouter_api_key", None)
    client_mod.get_client.cache_clear()
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        client_mod.get_client()
    client_mod.get_client.cache_clear()  # don't leak a cached state to other tests
