"""Schedule the end-of-day reminder via launchd (macOS) or cron (Linux).

`build_plist` / `build_cron_line` are pure (easy to test). `install_launchd` /
`uninstall_launchd` / `launchd_status` touch the filesystem + `launchctl`.
"""

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
    """A launchd agent that runs `shippost remind run` daily at hour:minute."""
    args = _run_args(repo=repo, tone=tone, model=model, open_x=open_x, program=program)
    args_xml = "\n".join(f"        <string>{a}</string>" for a in args)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        f"    <key>Label</key>\n    <string>{LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n"
        f"    <array>\n{args_xml}\n    </array>\n"
        f"    <key>WorkingDirectory</key>\n    <string>{repo}</string>\n"
        "    <key>StartCalendarInterval</key>\n"
        "    <dict>\n"
        f"        <key>Hour</key>\n        <integer>{hour}</integer>\n"
        f"        <key>Minute</key>\n        <integer>{minute}</integer>\n"
        "    </dict>\n"
        "    <key>RunAtLoad</key>\n    <false/>\n"
        "</dict>\n"
        "</plist>\n"
    )


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
    """A crontab line that runs the reminder daily at hour:minute."""
    args = _run_args(repo=repo, tone=tone, model=model, open_x=open_x, program=program)
    cmd = " ".join(args)
    return f"{minute} {hour} * * * cd {repo} && {cmd}"


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
