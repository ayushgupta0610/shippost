"""shippost CLI — `shippost draft`."""

import asyncio
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Annotated

import openai
import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel

from shippost.core import draft_post
from shippost.git_reader import GitError
from shippost.models import PostDraft
from shippost.voice import VoiceError

app = typer.Typer(
    add_completion=False,
    help="Draft build-in-public posts from your git commits.",
)
console = Console()


@app.callback()
def _callback() -> None:
    """shippost — turn git commits into build-in-public posts."""


_X_INTENT = "https://x.com/intent/tweet?text="
_VOICE_FILE = Path.home() / ".shippost" / "voice.txt"


def _load_voice_examples() -> list[str]:
    if _VOICE_FILE.is_file():
        lines = _VOICE_FILE.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if ln.strip()]
    return []


def _open_x(body: str) -> None:
    webbrowser.open(_X_INTENT + urllib.parse.quote(body))


def _show(draft: PostDraft) -> None:
    console.print(
        Panel(draft.body, title=f"draft ({draft.char_count} chars)", expand=False)
    )
    for i, variant in enumerate(draft.variants, start=1):
        console.print(
            Panel(
                variant,
                title=f"variant {i} ({len(variant)} chars)",
                expand=False,
            )
        )


@app.command()
def draft(
    since: Annotated[
        str | None, typer.Option(help="Git date expr, e.g. '1 day ago'.")
    ] = None,
    n: Annotated[
        int | None,
        typer.Option(help="Use the last N commits (default: last 5 when no --since)."),
    ] = None,
    tone: Annotated[
        str | None,
        typer.Option(help="Preset: technical|narrative|punchy|funny."),
    ] = None,
    prompt: Annotated[
        Path | None, typer.Option(help="Path to your own voice prompt file.")
    ] = None,
    model: Annotated[
        str | None, typer.Option(help="OpenRouter model slug.")
    ] = None,
    copy: Annotated[
        bool, typer.Option("--copy", help="Copy the draft to the clipboard.")
    ] = False,
    open_x: Annotated[
        bool,
        typer.Option("--open", help="Open X's compose window pre-filled."),
    ] = False,
    print_only: Annotated[
        bool, typer.Option("--print", help="Print the draft and exit.")
    ] = False,
) -> None:
    """Read recent commits and draft a build-in-public post."""
    try:
        with console.status("[dim]reading commits and drafting…[/dim]", spinner="dots"):
            result = asyncio.run(
                draft_post(
                    since=since,
                    n=n,
                    tone=tone,
                    prompt_path=prompt,
                    model=model,
                    voice_examples=_load_voice_examples(),
                )
            )
    except (GitError, VoiceError, ValueError, RuntimeError, openai.APIError) as exc:
        # openai.APIError covers auth/network/rate-limit failures (bad key, offline).
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    _show(result)

    if copy:
        try:
            pyperclip.copy(result.body)
            console.print("[green]copied to clipboard.[/green]")
        except pyperclip.PyperclipException as exc:
            # headless Linux / no clipboard backend — draft already printed above.
            console.print(f"[yellow]clipboard unavailable: {exc}[/yellow]")
    if open_x:
        _open_x(result.body)
        console.print("[green]opened X compose window.[/green]")
    if not (copy or open_x or print_only):
        console.print(
            "[dim]next: rerun with --copy or --open, or edit and post yourself.[/dim]"
        )


if __name__ == "__main__":
    app()
