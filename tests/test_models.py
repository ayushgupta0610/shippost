from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shippost.models import CommitContext, DraftPayload, PostDraft


def _commit() -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="add git reader",
    )


def test_commit_defaults():
    c = _commit()
    assert c.body == ""
    assert c.files_changed == []
    assert c.diff_summary == ""
    assert c.diff_truncated is False


def test_commit_is_frozen():
    c = _commit()
    with pytest.raises(ValidationError):
        c.subject = "changed"  # type: ignore[misc]


def test_commit_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CommitContext(
            sha="abc1234",
            author="Ayush",
            committed_at=datetime(2026, 6, 9, tzinfo=UTC),
            subject="x",
            bogus="nope",  # type: ignore[call-arg]
        )


def test_draft_payload_caps_variants():
    with pytest.raises(ValidationError):
        DraftPayload(body="hi", variants=["a", "b", "c"])


def test_draft_payload_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        DraftPayload(body="hi", bogus="nope")  # type: ignore[call-arg]


def test_post_draft_char_count_is_computed():
    d = PostDraft(body="hello", variants=[], model_used="x")
    assert d.char_count == 5


def test_post_draft_is_frozen():
    d = PostDraft(body="hello", variants=[], model_used="x")
    with pytest.raises(ValidationError):
        d.body = "changed"  # type: ignore[misc]
