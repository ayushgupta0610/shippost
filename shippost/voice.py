"""Assemble the system prompt: preset / user template + optional voice anchors.

The prompt files in `prompts/` and a user-supplied `--prompt` file are the
hackable heart of shippost: change the voice by editing markdown, not code.
"""

from pathlib import Path

PRESETS_DIR = Path(__file__).parent / "prompts"
DEFAULT_TONE = "technical"
VOICE_FILE = Path.home() / ".shippost" / "voice.txt"


def load_voice_examples() -> list[str]:
    """A few of the user's own posts (one per line) from ~/.shippost/voice.txt."""
    if VOICE_FILE.is_file():
        lines = VOICE_FILE.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if ln.strip()]
    return []


class VoiceError(RuntimeError):
    """Requested tone preset does not exist."""


def _load_preset(tone: str) -> str:
    path = PRESETS_DIR / f"{tone}.md"
    if not path.is_file():
        available = ", ".join(sorted(p.stem for p in PRESETS_DIR.glob("*.md")))
        raise VoiceError(f"Unknown tone '{tone}'. Available: {available}.")
    return path.read_text(encoding="utf-8")


def build_system_prompt(
    *,
    tone: str | None = None,
    prompt_path: Path | None = None,
    voice_examples: list[str] | None = None,
) -> str:
    if prompt_path is not None:
        if not prompt_path.is_file():
            raise VoiceError(f"Prompt file not found: {prompt_path}")
        base = prompt_path.read_text(encoding="utf-8")
    else:
        base = _load_preset(tone or DEFAULT_TONE)

    if voice_examples:
        anchors = "\n".join(f"- {ex.strip()}" for ex in voice_examples if ex.strip())
        if anchors:
            base += (
                "\n\nHere are examples of the user's own posts. Match this "
                f"voice closely:\n{anchors}\n"
            )
    return base
