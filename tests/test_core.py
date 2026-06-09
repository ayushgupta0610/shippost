from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from shiplog import core as core_mod
from shiplog.config import settings
from shiplog.git_reader import GitError
from shiplog.models import CommitContext, DraftPayload, PostDraft


def _commit() -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="add core",
    )


async def test_draft_post_wires_pieces_and_sets_model(monkeypatch):
    monkeypatch.setattr(core_mod, "read_commits", lambda **kw: [_commit()])
    monkeypatch.setattr(core_mod, "build_system_prompt", lambda **kw: "VOICE")
    monkeypatch.setattr(
        core_mod,
        "generate_draft",
        AsyncMock(return_value=DraftPayload(body="shipped core", variants=["core!"])),
    )

    result = await core_mod.draft_post(model="deepseek/deepseek-v4-flash")

    assert isinstance(result, PostDraft)
    assert result.body == "shipped core"
    assert result.variants == ["core!"]
    assert result.model_used == "deepseek/deepseek-v4-flash"
    assert result.char_count == len("shipped core")


async def test_draft_post_defaults_model_from_settings(monkeypatch):
    monkeypatch.setattr(core_mod, "read_commits", lambda **kw: [_commit()])
    monkeypatch.setattr(core_mod, "build_system_prompt", lambda **kw: "VOICE")
    monkeypatch.setattr(
        core_mod,
        "generate_draft",
        AsyncMock(return_value=DraftPayload(body="x", variants=[])),
    )
    result = await core_mod.draft_post()
    assert result.model_used == settings.default_model


async def test_draft_post_propagates_git_error(monkeypatch):
    def _boom(**kw):
        raise GitError("not a git repo")

    monkeypatch.setattr(core_mod, "read_commits", _boom)
    with pytest.raises(GitError):
        await core_mod.draft_post()
