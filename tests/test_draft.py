from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from shiplog import draft as draft_mod
from shiplog.llm.chat import LLMResult, TokenUsage
from shiplog.models import CommitContext, DraftPayload


def _commit(subject: str) -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject=subject,
        diff_summary="diff --git a b",
    )


async def test_generate_draft_calls_llm_and_returns_payload(monkeypatch):
    captured = {}

    async def fake_chat_structured(messages, response_model, *, model, max_retries=1):
        captured["messages"] = messages
        captured["model"] = model
        return LLMResult(
            data=DraftPayload(body="shipped a git reader", variants=["ship it"]),
            usage=TokenUsage(1, 1, 2),
            model=model,
        )

    monkeypatch.setattr(
        draft_mod, "chat_structured", AsyncMock(side_effect=fake_chat_structured)
    )

    payload = await draft_mod.generate_draft(
        [_commit("add git reader")],
        system_prompt="VOICE RULES",
        model="deepseek/deepseek-v4-flash",
    )

    assert isinstance(payload, DraftPayload)
    assert payload.body == "shipped a git reader"
    assert captured["model"] == "deepseek/deepseek-v4-flash"
    # system prompt must be first, commit content must reach the model
    assert captured["messages"][0]["role"] == "system"
    assert "VOICE RULES" in captured["messages"][0]["content"]
    assert "add git reader" in captured["messages"][1]["content"]


async def test_generate_draft_raises_on_no_commits():
    with pytest.raises(ValueError):
        await draft_mod.generate_draft([], system_prompt="x", model="m")


def test_render_commits_covers_no_files_truncated_and_multi():
    c1 = CommitContext(
        sha="deadbeef1234",
        author="A",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="first",
        diff_summary="d1",
        diff_truncated=True,
    )
    c2 = CommitContext(
        sha="cafef00d5678",
        author="A",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="second",
        files_changed=["x.py"],
        diff_summary="d2",
    )
    out = draft_mod._render_commits([c1, c2])
    assert "(no files)" in out          # c1 has no files
    assert "[diff truncated]" in out    # c1 is truncated
    assert "deadbee" in out             # sha[:7]
    assert "x.py" in out                # c2 files rendered
    assert "---" in out                 # multi-commit separator
