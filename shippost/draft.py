"""Turn commits into a DraftPayload with a single structured LLM call."""

from openai.types.chat import ChatCompletionMessageParam

from shippost.llm.chat import chat_structured
from shippost.models import CommitContext, DraftPayload


def _render_commits(commits: list[CommitContext]) -> str:
    blocks: list[str] = []
    for c in commits:
        files = ", ".join(c.files_changed) or "(no files)"
        block = (
            f"commit {c.sha[:7]} — {c.subject}\n"
            f"files: {files}\n"
            f"{c.body}\n"
            f"diff:\n{c.diff_summary}"
        )
        if c.diff_truncated:
            block += "\n[diff truncated]"
        blocks.append(block.strip())
    return "\n\n---\n\n".join(blocks)


async def generate_draft(
    commits: list[CommitContext],
    system_prompt: str,
    *,
    model: str,
) -> DraftPayload:
    if not commits:
        raise ValueError("Cannot draft a post with no commits.")

    user_content = (
        "Here is what I shipped. Write one build-in-public X post about it, "
        "plus up to two alternative phrasings.\n\n"
        f"{_render_commits(commits)}"
    )
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    result = await chat_structured(messages, DraftPayload, model=model)
    return result.data
