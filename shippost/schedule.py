"""Schedule the end-of-day reminder via launchd (macOS) or cron (Linux).

`build_plist` / `build_cron_line` are pure (easy to test). `install_launchd` /
`uninstall_launchd` / `launchd_status` touch the filesystem + `launchctl`.
"""

import plistlib
import shlex
import shutil
import subprocess
from pathlib import Path

LABEL = "com.shippost.remind"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _shippost_program() -> str:
    """Absolute path to the installed `shippost` executable (fallback: name)."""
    return shutil.which("shippost") or "shippost"


def _run_args(
    *,
    repo: Path,
    tone: str | None,
    model: str | None,
    open_x: bool,
    program: str | None,
) -> list[str]:
    args = [program or _shippost_program(), "remind", "run", "--repo", str(repo)]
    if tone:
        args += ["--tone", tone]
    if model:
        args += ["--model", model]
    if open_x:
        args += ["--open"]
    return args


def build_plist(
    *,
    hour: int,
    minute: int,
    repo: Path,
    tone: str | None = None,
    model: str | None = None,
    open_x: bool = False,
    program: str | None = None,
) -> str:
    """A launchd agent that runs `shippost remind run` daily at hour:minute.

    Built with plistlib so paths/args containing XML-special chars are escaped.
    """
    args = _run_args(repo=repo, tone=tone, model=model, open_x=open_x, program=program)
    data = {
        "Label": LABEL,
        "ProgramArguments": args,
        "WorkingDirectory": str(repo),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "RunAtLoad": False,
    }
    return plistlib.dumps(data).decode("utf-8")


def build_cron_line(
    *,
    hour: int,
    minute: int,
    repo: Path,
    tone: str | None = None,
    model: str | None = None,
    open_x: bool = False,
    program: str | None = None,
) -> str:
    """A crontab line that runs the reminder daily at hour:minute.

    Paths/args are shell-quoted so repos with spaces or special chars work.
    """
    args = _run_args(repo=repo, tone=tone, model=model, open_x=open_x, program=program)
    cmd = shlex.join(args)
    return f"{minute} {hour} * * * cd {shlex.quote(str(repo))} && {cmd}"


def install_launchd(plist_content: str) -> Path:
    """Write the plist and (re)load it via launchctl. Returns the plist path."""
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_text(plist_content, encoding="utf-8")
    # Unload first in case an old agent is loaded; ignore failure.
    subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        check=False,
        capture_output=True,
    )
    subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        check=False,
        capture_output=True,
    )
    return PLIST_PATH


def uninstall_launchd() -> bool:
    """Unload + remove the agent. Returns True if it existed."""
    if not PLIST_PATH.exists():
        return False
    subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        check=False,
        capture_output=True,
    )
    PLIST_PATH.unlink()
    return True


def launchd_status() -> dict[str, object]:
    return {"installed": PLIST_PATH.exists(), "path": str(PLIST_PATH)}
