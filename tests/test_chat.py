import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from shiplog.llm import chat as chat_mod


class _Out(BaseModel):
    value: int


def _fake_completion(content: str):
    """Mimic the openai response object shape we read from."""

    class _Msg:
        def __init__(self, c):
            self.content = c

    class _Choice:
        def __init__(self, c):
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5
        total_tokens = 15

    class _Resp:
        def __init__(self, c):
            self.choices = [_Choice(c)]
            self.usage = _Usage()
            self.model = "deepseek/deepseek-v4-flash"

    return _Resp(content)


@pytest.fixture
def mock_client(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(chat_mod, "get_client", lambda: client)
    return client


async def test_chat_structured_parses_valid_json(mock_client):
    mock_client.chat.completions.create.return_value = _fake_completion(
        json.dumps({"value": 42})
    )
    result = await chat_mod.chat_structured(
        [{"role": "user", "content": "give me 42"}],
        _Out,
        model="deepseek/deepseek-v4-flash",
    )
    assert result.data.value == 42
    assert result.usage.total == 15
    assert result.model == "deepseek/deepseek-v4-flash"


async def test_chat_structured_retries_then_succeeds(mock_client):
    mock_client.chat.completions.create.side_effect = [
        _fake_completion("not json at all"),
        _fake_completion(json.dumps({"value": 7})),
    ]
    result = await chat_mod.chat_structured(
        [{"role": "user", "content": "x"}],
        _Out,
        model="m",
        max_retries=1,
    )
    assert result.data.value == 7
    assert mock_client.chat.completions.create.call_count == 2


async def test_chat_structured_raises_after_retries(mock_client):
    mock_client.chat.completions.create.return_value = _fake_completion("garbage")
    with pytest.raises(ValueError):
        await chat_mod.chat_structured(
            [{"role": "user", "content": "x"}], _Out, model="m", max_retries=1
        )
