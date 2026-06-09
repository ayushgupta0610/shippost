"""The engine. CLI / Skill / MCP frontends all call `draft_post`."""

import asyncio
from pathlib import Path

from shippost.config import settings
from shippost.draft import generate_draft
from shippost.git_reader import read_commits
from shippost.models import PostDraft
from shippost.voice import build_system_prompt


async def draft_post(
    *,
    since: str | None = None,
    n: int | None = None,
    tone: str | None = None,
    prompt_path: Path | None = None,
    model: str | None = None,
    repo_path: Path | None = None,
    voice_examples: list[str] | None = None,
) -> PostDraft:
    """Read commits, build the voice prompt, and draft a post. Pure: no I/O side
    effects beyond reading git + calling the LLM."""
    chosen_model = model or settings.default_model

    # read_commits shells out (blocking); offload so async frontends (MCP/web)
    # don't stall their event loop.
    commits = await asyncio.to_thread(
        read_commits,
        since=since,
        n=n,
        repo_path=repo_path,
        max_diff_chars=settings.max_diff_chars,
    )
    system_prompt = build_system_prompt(
        tone=tone or settings.default_tone,
        prompt_path=prompt_path,
        voice_examples=voice_examples,
    )
    payload = await generate_draft(commits, system_prompt, model=chosen_model)
    return PostDraft(
        body=payload.body,
        variants=payload.variants,
        model_used=chosen_model,
    )
