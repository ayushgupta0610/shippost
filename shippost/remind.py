"""The `shippost remind` sub-app and the end-of-day reminder logic.

At a scheduled time it drafts a post from *today's* commits, copies it to the
clipboard, and fires a desktop notification. Silent when there are no commits.
"""

import asyncio
import sys
import urllib.parse
import webbrowser
from datetime import date
from pathlib import Path
from typing import Annotated

import openai
import pyperclip
import typer
from rich.console import Console

from shippost import schedule
from shippost.core import draft_post
from shippost.git_reader import GitError, NoCommitsError
from shippost.notify import send_notification
from shippost.voice import load_voice_examples

console = Console()
remind_app = typer.Typer(help="Schedule an end-of-day draft from today's commits.")

_X_INTENT = "https://x.com/intent/tweet?text="


def _today_start() -> str:
    """git --since expression for the start of today (local time)."""
    return f"{date.today().isoformat()} 00:00"


async def run_reminder(
    *,
    repo: Path | None = None,
    tone: str | None = None,
    model: str | None = None,
    open_x: bool = False,
) -> str:
    """Draft today's commits, copy to clipboard, notify.

    Returns "no-commits" (silent), "ok", or "error" (notified).
    """
    try:
        draft = await draft_post(
            since=_today_start(),
            repo_path=repo,
            tone=tone,
            model=model,
            voice_examples=load_voice_examples(),
        )
    except NoCommitsError:
        return "no-commits"  # nothing shipped today — no nag
    except (GitError, ValueError, RuntimeError, openai.APIError) as exc:
        send_notification("shippost", f"reminder failed: {exc}")
        return "error"

    try:
        pyperclip.copy(draft.body)
    except pyperclip.PyperclipException:
        pass  # no clipboard backend; notification still fires

    send_notification(
        "shippost",
        f"draft ready ({draft.char_count} chars) and copied to clipboard.",
    )
    if open_x:
        webbrowser.open(_X_INTENT + urllib.parse.quote(draft.body))
    return "ok"


def _parse_hhmm(at: str) -> tuple[int, int]:
    parts = at.split(":")
    if len(parts) != 2:
        raise typer.BadParameter("--at must be HH:MM, e.g. 18:00")
    try:
        hour, minute = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise typer.BadParameter("--at must be HH:MM, e.g. 18:00") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise typer.BadParameter("--at must be a valid 24h time, e.g. 18:00")
    return hour, minute


@remind_app.command("install")
def install_cmd(
    at: Annotated[str, typer.Option(help="Daily time, 24h HH:MM.")] = "18:00",
    repo: Annotated[
        Path | None, typer.Option(help="Repo to read (default: current dir).")
    ] = None,
    tone: Annotated[str | None, typer.Option(help="Voice preset.")] = None,
    model: Annotated[str | None, typer.Option(help="OpenRouter model slug.")] = None,
    open_x: Annotated[
        bool, typer.Option("--open", help="Also open X at reminder time.")
    ] = False,
) -> None:
    """Install the daily reminder (launchd on macOS, cron line on Linux)."""
    repo_path = (repo or Path.cwd()).resolve()
    hour, minute = _parse_hhmm(at)

    if sys.platform == "darwin":
        plist = schedule.build_plist(
            hour=hour, minute=minute, repo=repo_path,
            tone=tone, model=model, open_x=open_x,
        )
        path = schedule.install_launchd(plist)
        console.print(
            f"[green]installed[/green] daily reminder at {at} for {repo_path}\n"
            f"[dim]{path}[/dim]"
        )
    elif sys.platform.startswith("linux"):
        line = schedule.build_cron_line(
            hour=hour, minute=minute, repo=repo_path,
            tone=tone, model=model, open_x=open_x,
        )
        console.print("Add this line to your crontab ([dim]crontab -e[/dim]):")
        console.print(line)
    else:
        console.print(
            "[red]auto-install is supported on macOS and Linux only.[/red]"
        )
        raise typer.Exit(code=1)


@remind_app.command("uninstall")
def uninstall_cmd() -> None:
    """Remove the daily reminder (macOS)."""
    if sys.platform == "darwin":
        removed = schedule.uninstall_launchd()
        msg = "removed the reminder." if removed else "no reminder was installed."
        console.print(f"[green]{msg}[/green]")
    else:
        console.print("[dim]On Linux, remove the line from your crontab.[/dim]")


@remind_app.command("status")
def status_cmd() -> None:
    """Show whether the reminder is installed."""
    st = schedule.launchd_status()
    if st["installed"]:
        console.print(f"[green]installed[/green] [dim]{st['path']}[/dim]")
    else:
        console.print("[yellow]not installed[/yellow]")


@remind_app.command("run")
def run_cmd(
    repo: Annotated[
        Path | None, typer.Option(help="Repo to read (default: current dir).")
    ] = None,
    tone: Annotated[str | None, typer.Option(help="Voice preset.")] = None,
    model: Annotated[str | None, typer.Option(help="OpenRouter model slug.")] = None,
    open_x: Annotated[
        bool, typer.Option("--open", help="Open X's compose window.")
    ] = False,
) -> None:
    """Run the reminder now (what the scheduler invokes)."""
    status = asyncio.run(
        run_reminder(repo=repo, tone=tone, model=model, open_x=open_x)
    )
    console.print(f"[dim]{status}[/dim]")
