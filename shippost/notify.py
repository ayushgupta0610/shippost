"""Best-effort desktop notifications. Built-ins only, never raises.

macOS uses `osascript`; Linux uses `notify-send`. Other platforms / missing
binaries are silently a no-op (a background reminder must not crash on this).
"""

import subprocess
import sys


def _applescript_safe(s: str) -> str:
    """Neutralize a string for embedding in an AppleScript literal.

    AppleScript string literals have NO backslash escaping: a bare `"` ends the
    string, so escaping only quotes (as `\\"`) lets a crafted input break out and
    inject code. Since the message can be untrusted (e.g. git stderr from a
    cloned repo), strip backslashes, replace quotes, and collapse newlines.
    """
    return (
        s.replace("\\", "")
        .replace('"', "'")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def send_notification(title: str, message: str) -> None:
    """Show a desktop notification. Swallows all errors by design."""
    try:
        if sys.platform == "darwin":
            safe_title = _applescript_safe(title)
            safe_msg = _applescript_safe(message)
            script = f'display notification "{safe_msg}" with title "{safe_title}"'
            subprocess.run(
                ["osascript", "-e", script],
                check=False,
                capture_output=True,
            )
        elif sys.platform.startswith("linux"):
            subprocess.run(
                ["notify-send", title, message],
                check=False,
                capture_output=True,
            )
        # other platforms: no notification backend, stay silent
    except (FileNotFoundError, OSError):
        # notifier binary missing or unusable — never propagate
        pass
