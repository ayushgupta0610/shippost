from pathlib import Path

import pytest

from shippost import voice as voice_mod
from shippost.voice import VoiceError, build_system_prompt, load_voice_examples


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


def test_all_whitespace_examples_produce_no_block():
    prompt = build_system_prompt(voice_examples=["  ", ""])
    assert "Here are examples" not in prompt


def test_missing_prompt_file_raises_voice_error(tmp_path: Path):
    with pytest.raises(VoiceError):
        build_system_prompt(prompt_path=tmp_path / "does-not-exist.md")


def test_load_voice_examples_reads_nonempty_lines(monkeypatch, tmp_path):
    vf = tmp_path / "voice.txt"
    vf.write_text("post one\n\n  \npost two\n")
    monkeypatch.setattr(voice_mod, "VOICE_FILE", vf)
    assert load_voice_examples() == ["post one", "post two"]


def test_load_voice_examples_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_mod, "VOICE_FILE", tmp_path / "nope.txt")
    assert load_voice_examples() == []
