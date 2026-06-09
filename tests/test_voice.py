from pathlib import Path

import pytest

from shiplog.voice import VoiceError, build_system_prompt


def test_default_is_technical():
    prompt = build_system_prompt()
    assert "precise, technical" in prompt


def test_tone_selects_preset():
    prompt = build_system_prompt(tone="funny")
    assert "self-deprecating" in prompt


def test_unknown_tone_raises():
    with pytest.raises(VoiceError):
        build_system_prompt(tone="nope")


def test_explicit_prompt_file_wins(tmp_path: Path):
    custom = tmp_path / "mine.md"
    custom.write_text("MY OWN VOICE RULES")
    prompt = build_system_prompt(tone="funny", prompt_path=custom)
    assert "MY OWN VOICE RULES" in prompt
    assert "self-deprecating" not in prompt


def test_voice_examples_are_appended():
    prompt = build_system_prompt(voice_examples=["just shipped a parser", "ship it"])
    assert "just shipped a parser" in prompt
    assert "ship it" in prompt
