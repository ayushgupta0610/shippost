from unittest.mock import AsyncMock

from shippost import remind as remind_mod
from shippost.git_reader import GitError
from shippost.models import PostDraft


def _patch_common(monkeypatch):
    # hermetic: don't read the real ~/.shippost/voice.txt
    monkeypatch.setattr(remind_mod, "load_voice_examples", lambda: [])


async def test_run_reminder_drafts_copies_notifies(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        remind_mod,
        "draft_post",
        AsyncMock(
            return_value=PostDraft(body="today I shipped", variants=[], model_used="m")
        ),
    )
    copied = {}
    notes = []
    monkeypatch.setattr(
        remind_mod.pyperclip, "copy", lambda t: copied.setdefault("t", t)
    )
    monkeypatch.setattr(
        remind_mod, "send_notification", lambda title, msg: notes.append((title, msg))
    )

    status = await remind_mod.run_reminder()
    assert status == "ok"
    assert copied["t"] == "today I shipped"
    assert len(notes) == 1


async def test_run_reminder_silent_when_no_commits(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        remind_mod,
        "draft_post",
        AsyncMock(side_effect=GitError("No commits found for the given range.")),
    )
    notes = []
    monkeypatch.setattr(
        remind_mod, "send_notification", lambda t, m: notes.append((t, m))
    )

    status = await remind_mod.run_reminder()
    assert status == "no-commits"
    assert notes == []


async def test_run_reminder_notifies_on_error(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        remind_mod,
        "draft_post",
        AsyncMock(side_effect=RuntimeError("OPENROUTER_API_KEY is not set")),
    )
    notes = []
    monkeypatch.setattr(
        remind_mod, "send_notification", lambda t, m: notes.append((t, m))
    )

    status = await remind_mod.run_reminder()
    assert status == "error"
    assert len(notes) == 1
    assert "OPENROUTER_API_KEY" in notes[0][1]
