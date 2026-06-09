from unittest.mock import AsyncMock

from typer.testing import CliRunner

from shippost import cli as cli_mod
from shippost.models import PostDraft

runner = CliRunner()


def test_draft_print_outputs_body(monkeypatch):
    monkeypatch.setattr(
        cli_mod,
        "draft_post",
        AsyncMock(
            return_value=PostDraft(
                body="shipped the cli", variants=["cli!"], model_used="m"
            )
        ),
    )
    result = runner.invoke(cli_mod.app, ["draft", "--print", "--n", "1"])
    assert result.exit_code == 0
    assert "shipped the cli" in result.stdout


def test_draft_copy_uses_clipboard(monkeypatch):
    monkeypatch.setattr(
        cli_mod,
        "draft_post",
        AsyncMock(return_value=PostDraft(body="copy me", variants=[], model_used="m")),
    )
    copied = {}
    monkeypatch.setattr(
        cli_mod.pyperclip,
        "copy",
        lambda text: copied.setdefault("text", text),
    )
    result = runner.invoke(cli_mod.app, ["draft", "--copy"])
    assert result.exit_code == 0
    assert copied["text"] == "copy me"


def test_draft_open_x_calls_webbrowser(monkeypatch):
    monkeypatch.setattr(
        cli_mod,
        "draft_post",
        AsyncMock(
            return_value=PostDraft(body="hello world", variants=[], model_used="m")
        ),
    )
    opened = {}
    monkeypatch.setattr(
        cli_mod.webbrowser, "open", lambda url: opened.setdefault("url", url)
    )
    result = runner.invoke(cli_mod.app, ["draft", "--open"])
    assert result.exit_code == 0
    assert "hello%20world" in opened["url"]


def test_draft_reports_git_error(monkeypatch):
    from shippost.git_reader import GitError

    monkeypatch.setattr(
        cli_mod,
        "draft_post",
        AsyncMock(side_effect=GitError("not a git repo")),
    )
    result = runner.invoke(cli_mod.app, ["draft", "--print"])
    assert result.exit_code == 1
    assert "not a git repo" in result.stdout
