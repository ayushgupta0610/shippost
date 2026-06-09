"""Best-effort desktop notifications. Built-ins only, never raises.

macOS uses `osascript`; Linux uses `notify-send`. Other platforms / missing
binaries are silently a no-op (a background reminder must not crash on this).
"""

import subprocess
import sys


def send_notification(title: str, message: str) -> None:
    """Show a desktop notification. Swallows all errors by design."""
    try:
        if sys.platform == "darwin":
            safe_title = title.replace('"', '\\"')
            safe_msg = message.replace('"', '\\"')
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
