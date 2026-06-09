# shiplog v1 (Engine + CLI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a zero-config CLI that turns recent local git commits into a creative, voice-matched build-in-public X post the user edits and posts themselves.

**Architecture:** A pure engine (`shiplog.core.draft_post`) reads commits via `git` subprocess, assembles a hackable voice prompt, and makes a single structured LLM call through OpenRouter. The CLI (`shiplog draft`) is the only v1 frontend; Skill and MCP adapters are deferred (see spec). No DB, no agent loop, no X API.

**Tech Stack:** Python 3.13, `uv`, `ruff`, `pyright`, `pytest`. Runtime: `typer`, `rich`, `openai` (OpenRouter transport), `pydantic` + `pydantic-settings`, `pyperclip`. Default model `deepseek/deepseek-v4-flash`.

**Repo root:** `/Users/gupta/Downloads/Development/Projects/shiplog`
**Package dir:** `shiplog/` (i.e. `shiplog/shiplog/...`)

---

## File structure (locked)

```
shiplog/                      # repo root (already a git repo with the spec)
  pyproject.toml              # Task 1
  .env.example                # Task 11
  README.md  LICENSE          # Task 11
  shiplog/                    # the package
    __init__.py               # Task 1
    config.py                 # Task 2  — Settings (env)
    models.py                 # Task 3  — CommitContext, PostDraft, DraftPayload
    llm/
      __init__.py             # Task 4
      client.py               # Task 4  — AsyncOpenAI -> OpenRouter
      chat.py                 # Task 4  — chat_structured + LLMResult/TokenUsage
    git_reader.py             # Task 5  — read_commits()
    voice.py                  # Task 6  — build_system_prompt()
    prompts/                  # Task 6  — technical.md, narrative.md, punchy.md, funny.md
    draft.py                  # Task 7  — generate_draft()
    core.py                   # Task 8  — draft_post() orchestrator
    cli.py                    # Task 9  — Typer app
  tests/
    test_config.py            # Task 2
    test_models.py            # Task 3
    test_chat.py              # Task 4
    test_git_reader.py        # Task 5
    test_voice.py             # Task 6
    test_draft.py             # Task 7
    test_core.py              # Task 8
    test_cli.py               # Task 9
```

**Public type contract (used across tasks — keep names exact):**
- `CommitContext(sha, author, committed_at, subject, body, files_changed, diff_summary, diff_truncated)`
- `DraftPayload(body, variants)` — what the LLM returns
- `PostDraft(body, variants, model_used)` with computed `.char_count`
- `chat_structured(messages, response_model, *, model, max_retries=1) -> LLMResult[T]`
- `read_commits(*, since=None, n=None, repo_path=None, max_diff_chars=4000) -> list[CommitContext]`
- `build_system_prompt(*, tone=None, prompt_path=None, voice_examples=None) -> str`
- `generate_draft(commits, system_prompt, *, model) -> DraftPayload`
- `draft_post(*, since=None, n=None, tone=None, prompt_path=None, model=None, repo_path=None, voice_examples=None) -> PostDraft`

---

### Task 1: Project scaffold + tooling

**Files:**
- Create: `pyproject.toml`
- Create: `shiplog/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "shiplog"
version = "0.1.0"
description = "Turn your git commits into a creative build-in-public X post."
readme = "README.md"
requires-python = ">=3.13"
license = { text = "MIT" }
dependencies = [
    "typer>=0.20.0",
    "rich>=14.0.0",
    "openai>=2.41.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.14.0",
    "pyperclip>=1.9.0",
]

[project.scripts]
shiplog = "shiplog.cli:app"

[dependency-groups]
dev = [
    "pytest>=9.0.0",
    "pytest-asyncio>=1.0.0",
    "pyright>=1.1.409",
    "ruff>=0.15.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pyright]
include = ["shiplog", "tests"]
typeCheckingMode = "standard"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create package + test init files**

`shiplog/__init__.py`:
```python
"""shiplog — git commits to a build-in-public post."""

__version__ = "0.1.0"
```

`tests/__init__.py`: (empty file)

- [ ] **Step 3: Write a smoke test**

`tests/test_smoke.py`:
```python
import shiplog


def test_version_is_exposed():
    assert shiplog.__version__ == "0.1.0"
```

- [ ] **Step 4: Sync and run**

Run: `cd /Users/gupta/Downloads/Development/Projects/shiplog && uv sync && uv run pytest tests/test_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock shiplog/__init__.py tests/
git commit -m "chore: scaffold shiplog package + tooling"
```

---

### Task 2: Config

**Files:**
- Create: `shiplog/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
from shiplog.config import Settings


def test_defaults_are_sane():
    s = Settings(_env_file=None)  # ignore any real .env
    assert s.default_model == "deepseek/deepseek-v4-flash"
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert s.default_tone == "technical"
    assert s.max_diff_chars == 4000


def test_api_key_optional_at_construction():
    s = Settings(_env_file=None)
    assert s.openrouter_api_key is None


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("DEFAULT_MODEL", "openai/gpt-5")
    s = Settings(_env_file=None)
    assert s.openrouter_api_key == "sk-test"
    assert s.default_model == "openai/gpt-5"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.config'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/config.py`:
```python
"""Application configuration. The only module that reads the environment."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str | None = Field(default=None)
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    default_model: str = Field(default="deepseek/deepseek-v4-flash")
    default_tone: str = Field(default="technical")
    max_diff_chars: int = Field(default=4000)


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/config.py tests/test_config.py
git commit -m "feat: config via pydantic-settings"
```

---

### Task 3: Domain models

**Files:**
- Create: `shiplog/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from shiplog.models import CommitContext, DraftPayload, PostDraft


def _commit() -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="add git reader",
    )


def test_commit_defaults():
    c = _commit()
    assert c.body == ""
    assert c.files_changed == []
    assert c.diff_truncated is False


def test_commit_is_frozen():
    c = _commit()
    with pytest.raises(ValidationError):
        c.subject = "changed"  # type: ignore[misc]


def test_commit_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CommitContext(
            sha="abc1234",
            author="Ayush",
            committed_at=datetime(2026, 6, 9, tzinfo=UTC),
            subject="x",
            bogus="nope",  # type: ignore[call-arg]
        )


def test_draft_payload_caps_variants():
    with pytest.raises(ValidationError):
        DraftPayload(body="hi", variants=["a", "b", "c"])


def test_post_draft_char_count_is_computed():
    d = PostDraft(body="hello", variants=[], model_used="x")
    assert d.char_count == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.models'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/models.py`:
```python
"""Domain models. All frozen + extra-forbid (immutable, strict)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CommitContext(BaseModel):
    """One commit shaped for LLM consumption."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sha: str
    author: str
    committed_at: datetime
    subject: str
    body: str = ""
    files_changed: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    diff_truncated: bool = False


class DraftPayload(BaseModel):
    """Exactly what the LLM is asked to return."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(description="The post body, ready to publish.")
    variants: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Up to two alternative phrasings.",
    )


class PostDraft(BaseModel):
    """The engine's return value: a draft plus provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    body: str
    variants: list[str] = Field(default_factory=list)
    model_used: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def char_count(self) -> int:
        return len(self.body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/models.py tests/test_models.py
git commit -m "feat: domain models (CommitContext, DraftPayload, PostDraft)"
```

---

### Task 4: LLM layer (OpenRouter + structured output)

**Files:**
- Create: `shiplog/llm/__init__.py`
- Create: `shiplog/llm/client.py`
- Create: `shiplog/llm/chat.py`
- Test: `tests/test_chat.py`

**Approach note:** DeepSeek and most OpenRouter models support `response_format={"type": "json_object"}` but not always OpenAI strict schema parsing. So `chat_structured` requests JSON mode, injects the target schema into the messages, validates with Pydantic, and retries once with a corrective message on validation failure. This keeps it provider-agnostic.

- [ ] **Step 1: Write the failing test**

`tests/test_chat.py`:
```python
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from shiplog.llm import chat as chat_mod


class _Out(BaseModel):
    value: int


def _fake_completion(content: str):
    """Mimic the openai response object shape we read from."""

    class _Msg:
        def __init__(self, c):
            self.content = c

    class _Choice:
        def __init__(self, c):
            self.message = _Msg(c)

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5
        total_tokens = 15

    class _Resp:
        def __init__(self, c):
            self.choices = [_Choice(c)]
            self.usage = _Usage()
            self.model = "deepseek/deepseek-v4-flash"

    return _Resp(content)


@pytest.fixture
def mock_client(monkeypatch):
    client = AsyncMock()
    monkeypatch.setattr(chat_mod, "get_client", lambda: client)
    return client


async def test_chat_structured_parses_valid_json(mock_client):
    mock_client.chat.completions.create.return_value = _fake_completion(
        json.dumps({"value": 42})
    )
    result = await chat_mod.chat_structured(
        [{"role": "user", "content": "give me 42"}],
        _Out,
        model="deepseek/deepseek-v4-flash",
    )
    assert result.data.value == 42
    assert result.usage.total == 15
    assert result.model == "deepseek/deepseek-v4-flash"


async def test_chat_structured_retries_then_succeeds(mock_client):
    mock_client.chat.completions.create.side_effect = [
        _fake_completion("not json at all"),
        _fake_completion(json.dumps({"value": 7})),
    ]
    result = await chat_mod.chat_structured(
        [{"role": "user", "content": "x"}],
        _Out,
        model="m",
        max_retries=1,
    )
    assert result.data.value == 7
    assert mock_client.chat.completions.create.call_count == 2


async def test_chat_structured_raises_after_retries(mock_client):
    mock_client.chat.completions.create.return_value = _fake_completion("garbage")
    with pytest.raises(ValueError):
        await chat_mod.chat_structured(
            [{"role": "user", "content": "x"}], _Out, model="m", max_retries=1
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_chat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.llm'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/llm/client.py`:
```python
"""Async OpenAI SDK client pointed at OpenRouter. The only LLM transport."""

from functools import lru_cache

from openai import AsyncOpenAI

from shiplog.config import settings


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Add it to .env before drafting."
        )
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
```

`shiplog/llm/chat.py`:
```python
"""High-level structured chat over OpenRouter (JSON mode + Pydantic validate)."""

import json
from dataclasses import dataclass
from typing import Generic, TypeVar

from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from shiplog.llm.client import get_client

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class TokenUsage:
    prompt: int
    completion: int
    total: int


@dataclass(frozen=True)
class LLMResult(Generic[T]):
    data: T
    usage: TokenUsage
    model: str


async def chat_structured(
    messages: list[ChatCompletionMessageParam],
    response_model: type[T],
    *,
    model: str,
    max_retries: int = 1,
) -> LLMResult[T]:
    """Call the model in JSON mode and validate into `response_model`.

    Retries up to `max_retries` times with a corrective message when the
    model returns content that does not validate.
    """
    client = get_client()
    schema = json.dumps(response_model.model_json_schema())
    convo: list[ChatCompletionMessageParam] = [
        *messages,
        {
            "role": "system",
            "content": (
                "Respond with ONLY a JSON object that matches this JSON "
                f"schema (no prose, no code fences): {schema}"
            ),
        },
    ]

    last_error = "unknown error"
    for attempt in range(max_retries + 1):
        resp = await client.chat.completions.create(
            model=model,
            messages=convo,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        try:
            data = response_model.model_validate_json(raw)
        except ValidationError as exc:
            last_error = str(exc)
            convo.append({"role": "assistant", "content": raw})
            convo.append(
                {
                    "role": "user",
                    "content": (
                        "That did not match the schema. Return ONLY valid "
                        f"JSON for the schema. Error: {last_error}"
                    ),
                }
            )
            continue

        usage = resp.usage
        return LLMResult(
            data=data,
            usage=TokenUsage(
                prompt=getattr(usage, "prompt_tokens", 0) or 0,
                completion=getattr(usage, "completion_tokens", 0) or 0,
                total=getattr(usage, "total_tokens", 0) or 0,
            ),
            model=resp.model or model,
        )

    raise ValueError(
        f"Model did not return valid JSON after {max_retries + 1} attempts: "
        f"{last_error}"
    )
```

`shiplog/llm/__init__.py`:
```python
"""LLM access for shiplog."""

from shiplog.llm.chat import LLMResult, TokenUsage, chat_structured
from shiplog.llm.client import get_client

__all__ = ["LLMResult", "TokenUsage", "chat_structured", "get_client"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_chat.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/llm tests/test_chat.py
git commit -m "feat: structured chat over OpenRouter (JSON mode + retry)"
```

---

### Task 5: Git reader

**Files:**
- Create: `shiplog/git_reader.py`
- Test: `tests/test_git_reader.py`

**Design:** `read_commits` shells out to `git log` with a record/field separator format, then fetches a per-commit stat+patch capped at `max_diff_chars` total. Returns `CommitContext` list, newest first. Raises `GitError` for "not a repo" / no commits.

- [ ] **Step 1: Write the failing test**

`tests/test_git_reader.py`:
```python
import subprocess
from pathlib import Path

import pytest

from shiplog.git_reader import GitError, read_commits


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "a@b.c")
    _git(tmp_path, "config", "user.name", "Ayush")
    (tmp_path / "a.txt").write_text("hello\n")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-m", "first commit")
    (tmp_path / "b.txt").write_text("world\n")
    _git(tmp_path, "add", "b.txt")
    _git(tmp_path, "commit", "-m", "second commit")
    return tmp_path


def test_reads_commits_newest_first(repo: Path):
    commits = read_commits(repo_path=repo)
    assert [c.subject for c in commits] == ["second commit", "first commit"]
    assert commits[0].author == "Ayush"
    assert "b.txt" in commits[0].files_changed


def test_n_limits_count(repo: Path):
    commits = read_commits(n=1, repo_path=repo)
    assert len(commits) == 1
    assert commits[0].subject == "second commit"


def test_diff_truncation_flag(repo: Path):
    commits = read_commits(repo_path=repo, max_diff_chars=1)
    assert commits[0].diff_truncated is True
    assert len(commits[0].diff_summary) <= 1


def test_not_a_git_repo(tmp_path: Path):
    with pytest.raises(GitError):
        read_commits(repo_path=tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_git_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.git_reader'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/git_reader.py`:
```python
"""Read local git history via subprocess. No GitHub API, no auth."""

import subprocess
from datetime import datetime
from pathlib import Path

from shiplog.models import CommitContext

_RS = "\x1e"  # record separator
_FS = "\x1f"  # field separator
_FORMAT = _FS.join(["%H", "%an", "%aI", "%s", "%b"]) + _RS


class GitError(RuntimeError):
    """A git command failed or the path is not a repository."""


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or "git command failed")
    return result.stdout


def _files_for(repo: Path, sha: str) -> list[str]:
    out = _run_git(repo, "show", "--no-color", "--name-only", "--format=", sha)
    return [line for line in out.splitlines() if line.strip()]


def _diff_for(repo: Path, sha: str, max_chars: int) -> tuple[str, bool]:
    out = _run_git(repo, "show", "--no-color", "--stat", "--patch", "--format=", sha)
    if len(out) > max_chars:
        return out[:max_chars], True
    return out, False


def read_commits(
    *,
    since: str | None = None,
    n: int | None = None,
    repo_path: Path | None = None,
    max_diff_chars: int = 4000,
) -> list[CommitContext]:
    """Return commits newest-first. `since` is any git date expr; `n` caps count."""
    repo = repo_path or Path.cwd()

    args = ["log", f"--pretty=format:{_FORMAT}"]
    if since:
        args.append(f"--since={since}")
    if n:
        args.append(f"-n{n}")

    raw = _run_git(repo, *args)
    records = [r for r in raw.split(_RS) if r.strip()]
    if not records:
        raise GitError("No commits found for the given range.")

    commits: list[CommitContext] = []
    for record in records:
        sha, author, iso, subject, body = (record.strip().split(_FS) + ["", "", "", "", ""])[:5]
        diff_summary, truncated = _diff_for(repo, sha, max_diff_chars)
        commits.append(
            CommitContext(
                sha=sha,
                author=author,
                committed_at=datetime.fromisoformat(iso),
                subject=subject,
                body=body.strip(),
                files_changed=_files_for(repo, sha),
                diff_summary=diff_summary,
                diff_truncated=truncated,
            )
        )
    return commits
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_git_reader.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/git_reader.py tests/test_git_reader.py
git commit -m "feat: read local commits + capped diffs via git subprocess"
```

---

### Task 6: Voice layer + prompt presets

**Files:**
- Create: `shiplog/prompts/technical.md`
- Create: `shiplog/prompts/narrative.md`
- Create: `shiplog/prompts/punchy.md`
- Create: `shiplog/prompts/funny.md`
- Create: `shiplog/voice.py`
- Test: `tests/test_voice.py`

**Resolution order:** explicit `prompt_path` > `tone` preset > default preset (`technical`). Voice examples, if any, are appended as few-shot anchors.

- [ ] **Step 1: Create the four preset files**

`shiplog/prompts/technical.md`:
```markdown
You write build-in-public posts for X (Twitter) from a developer's git commits.

Voice: precise, technical, and humble. Explain what was actually built and why
it matters, in plain language a fellow engineer respects. No hype words, no
emojis spam, no "thrilled to announce". Lowercase is fine.

Rules:
- Under 280 characters for the main body.
- No em dashes, no semicolons.
- Lead with the concrete thing shipped, not a preamble.
- It is fine for the work to be small. Small ships still count.
```

`shiplog/prompts/narrative.md`:
```markdown
You write build-in-public posts for X (Twitter) from a developer's git commits.

Voice: a short story. One small arc — what you set out to do, the snag, what you
shipped. Honest and human, never corporate.

Rules:
- Under 280 characters for the main body.
- No em dashes, no semicolons.
- One idea, told as a mini narrative.
- It is fine for the work to be small.
```

`shiplog/prompts/punchy.md`:
```markdown
You write build-in-public posts for X (Twitter) from a developer's git commits.

Voice: short, sharp, confident. Strong first line that could stand alone. Cut
every spare word.

Rules:
- Under 280 characters for the main body.
- No em dashes, no semicolons.
- First line is a hook. Keep it punchy.
- It is fine for the work to be small.
```

`shiplog/prompts/funny.md`:
```markdown
You write build-in-public posts for X (Twitter) from a developer's git commits.

Voice: self-deprecating dev humor. Make the reader smile while still saying what
shipped. Never cringe, never forced.

Rules:
- Under 280 characters for the main body.
- No em dashes, no semicolons.
- A little wit, but the ship is still clear.
- It is fine for the work to be small.
```

- [ ] **Step 2: Write the failing test**

`tests/test_voice.py`:
```python
from pathlib import Path

import pytest

from shiplog.voice import VoiceError, build_system_prompt


def test_default_is_technical():
    prompt = build_system_prompt()
    assert "precise, technical" in prompt


def test_tone_selects_preset():
    prompt = build_system_prompt(tone="funny")
    assert "self-deprecating" in prompt


def test_unknown_tone_raises():
    with pytest.raises(VoiceError):
        build_system_prompt(tone="nope")


def test_explicit_prompt_file_wins(tmp_path: Path):
    custom = tmp_path / "mine.md"
    custom.write_text("MY OWN VOICE RULES")
    prompt = build_system_prompt(tone="funny", prompt_path=custom)
    assert "MY OWN VOICE RULES" in prompt
    assert "self-deprecating" not in prompt


def test_voice_examples_are_appended():
    prompt = build_system_prompt(voice_examples=["just shipped a parser", "ship it"])
    assert "just shipped a parser" in prompt
    assert "ship it" in prompt
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_voice.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.voice'`.

- [ ] **Step 4: Write minimal implementation**

`shiplog/voice.py`:
```python
"""Assemble the system prompt: preset / user template + optional voice anchors.

The prompt files in `prompts/` and a user-supplied `--prompt` file are the
hackable heart of shiplog: change the voice by editing markdown, not code.
"""

from pathlib import Path

PRESETS_DIR = Path(__file__).parent / "prompts"
DEFAULT_TONE = "technical"


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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_voice.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add shiplog/voice.py shiplog/prompts tests/test_voice.py
git commit -m "feat: voice layer with hackable markdown presets"
```

---

### Task 7: Draft generation

**Files:**
- Create: `shiplog/draft.py`
- Test: `tests/test_draft.py`

- [ ] **Step 1: Write the failing test**

`tests/test_draft.py`:
```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from shiplog import draft as draft_mod
from shiplog.llm.chat import LLMResult, TokenUsage
from shiplog.models import CommitContext, DraftPayload


def _commit(subject: str) -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject=subject,
        diff_summary="diff --git a b",
    )


async def test_generate_draft_calls_llm_and_returns_payload(monkeypatch):
    captured = {}

    async def fake_chat_structured(messages, response_model, *, model, max_retries=1):
        captured["messages"] = messages
        captured["model"] = model
        return LLMResult(
            data=DraftPayload(body="shipped a git reader", variants=["ship it"]),
            usage=TokenUsage(1, 1, 2),
            model=model,
        )

    monkeypatch.setattr(draft_mod, "chat_structured", AsyncMock(side_effect=fake_chat_structured))

    payload = await draft_mod.generate_draft(
        [_commit("add git reader")],
        system_prompt="VOICE RULES",
        model="deepseek/deepseek-v4-flash",
    )

    assert isinstance(payload, DraftPayload)
    assert payload.body == "shipped a git reader"
    assert captured["model"] == "deepseek/deepseek-v4-flash"
    # system prompt must be first, commit content must reach the model
    assert captured["messages"][0]["role"] == "system"
    assert "VOICE RULES" in captured["messages"][0]["content"]
    assert "add git reader" in captured["messages"][1]["content"]


async def test_generate_draft_raises_on_no_commits():
    with pytest.raises(ValueError):
        await draft_mod.generate_draft([], system_prompt="x", model="m")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_draft.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.draft'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/draft.py`:
```python
"""Turn commits into a DraftPayload with a single structured LLM call."""

from openai.types.chat import ChatCompletionMessageParam

from shiplog.llm.chat import chat_structured
from shiplog.models import CommitContext, DraftPayload


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_draft.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/draft.py tests/test_draft.py
git commit -m "feat: draft generation from commits (single structured call)"
```

---

### Task 8: Engine orchestrator (`core.draft_post`)

**Files:**
- Create: `shiplog/core.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Write the failing test**

`tests/test_core.py`:
```python
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from shiplog import core as core_mod
from shiplog.models import CommitContext, DraftPayload, PostDraft


def _commit() -> CommitContext:
    return CommitContext(
        sha="abc1234",
        author="Ayush",
        committed_at=datetime(2026, 6, 9, tzinfo=UTC),
        subject="add core",
    )


async def test_draft_post_wires_pieces_and_sets_model(monkeypatch):
    monkeypatch.setattr(core_mod, "read_commits", lambda **kw: [_commit()])
    monkeypatch.setattr(core_mod, "build_system_prompt", lambda **kw: "VOICE")
    monkeypatch.setattr(
        core_mod,
        "generate_draft",
        AsyncMock(return_value=DraftPayload(body="shipped core", variants=["core!"])),
    )

    result = await core_mod.draft_post(model="deepseek/deepseek-v4-flash")

    assert isinstance(result, PostDraft)
    assert result.body == "shipped core"
    assert result.variants == ["core!"]
    assert result.model_used == "deepseek/deepseek-v4-flash"
    assert result.char_count == len("shipped core")


async def test_draft_post_defaults_model_from_settings(monkeypatch):
    monkeypatch.setattr(core_mod, "read_commits", lambda **kw: [_commit()])
    monkeypatch.setattr(core_mod, "build_system_prompt", lambda **kw: "VOICE")
    monkeypatch.setattr(
        core_mod,
        "generate_draft",
        AsyncMock(return_value=DraftPayload(body="x", variants=[])),
    )
    result = await core_mod.draft_post()
    assert result.model_used == "deepseek/deepseek-v4-flash"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_core.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.core'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/core.py`:
```python
"""The engine. CLI / Skill / MCP frontends all call `draft_post`."""

from pathlib import Path

from shiplog.config import settings
from shiplog.draft import generate_draft
from shiplog.git_reader import read_commits
from shiplog.models import PostDraft
from shiplog.voice import build_system_prompt


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

    commits = read_commits(
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_core.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add shiplog/core.py tests/test_core.py
git commit -m "feat: draft_post engine orchestrator"
```

---

### Task 9: CLI

**Files:**
- Create: `shiplog/cli.py`
- Test: `tests/test_cli.py`

**Design:** Typer app with one command, `draft`. Non-interactive output is controlled by `--print` (stdout), `--copy` (clipboard), `--open` (browser to X intent). Default (no output flag) prints the draft and the available next-step hints. The interactive review loop is kept thin and is exercised separately; the test covers the `--print` path with the engine mocked so no network/clipboard is touched.

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:
```python
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from shiplog import cli as cli_mod
from shiplog.models import PostDraft

runner = CliRunner()


def test_draft_print_outputs_body(monkeypatch):
    monkeypatch.setattr(
        cli_mod,
        "draft_post",
        AsyncMock(return_value=PostDraft(body="shipped the cli", variants=["cli!"], model_used="m")),
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
    monkeypatch.setattr(cli_mod.pyperclip, "copy", lambda text: copied.setdefault("text", text))
    result = runner.invoke(cli_mod.app, ["draft", "--copy"])
    assert result.exit_code == 0
    assert copied["text"] == "copy me"


def test_draft_reports_git_error(monkeypatch):
    from shiplog.git_reader import GitError

    monkeypatch.setattr(cli_mod, "draft_post", AsyncMock(side_effect=GitError("not a git repo")))
    result = runner.invoke(cli_mod.app, ["draft", "--print"])
    assert result.exit_code == 1
    assert "not a git repo" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'shiplog.cli'`.

- [ ] **Step 3: Write minimal implementation**

`shiplog/cli.py`:
```python
"""shiplog CLI — `shiplog draft`."""

import asyncio
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Annotated

import pyperclip
import typer
from rich.console import Console
from rich.panel import Panel

from shiplog.core import draft_post
from shiplog.git_reader import GitError
from shiplog.models import PostDraft
from shiplog.voice import VoiceError

app = typer.Typer(add_completion=False, help="Draft build-in-public posts from your git commits.")
console = Console()

_X_INTENT = "https://x.com/intent/tweet?text="
_VOICE_FILE = Path.home() / ".shiplog" / "voice.txt"


def _load_voice_examples() -> list[str]:
    if _VOICE_FILE.is_file():
        return [ln for ln in _VOICE_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return []


def _open_x(body: str) -> None:
    webbrowser.open(_X_INTENT + urllib.parse.quote(body))


def _show(draft: PostDraft) -> None:
    console.print(Panel(draft.body, title=f"draft ({draft.char_count} chars)", expand=False))
    for i, variant in enumerate(draft.variants, start=1):
        console.print(Panel(variant, title=f"variant {i} ({len(variant)} chars)", expand=False))


@app.command()
def draft(
    since: Annotated[str | None, typer.Option(help="Git date expr, e.g. '1 day ago'.")] = None,
    n: Annotated[int | None, typer.Option(help="Use the last N commits.")] = None,
    tone: Annotated[str | None, typer.Option(help="Preset: technical|narrative|punchy|funny.")] = None,
    prompt: Annotated[Path | None, typer.Option(help="Path to your own voice prompt file.")] = None,
    model: Annotated[str | None, typer.Option(help="OpenRouter model slug.")] = None,
    copy: Annotated[bool, typer.Option("--copy", help="Copy the draft to the clipboard.")] = False,
    open_x: Annotated[bool, typer.Option("--open", help="Open X's compose window pre-filled.")] = False,
    print_only: Annotated[bool, typer.Option("--print", help="Print the draft and exit.")] = False,
) -> None:
    """Read recent commits and draft a build-in-public post."""
    try:
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
    except (GitError, VoiceError, ValueError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    _show(result)

    if copy:
        pyperclip.copy(result.body)
        console.print("[green]copied to clipboard.[/green]")
    if open_x:
        _open_x(result.body)
        console.print("[green]opened X compose window.[/green]")
    if not (copy or open_x or print_only):
        console.print("[dim]next: rerun with --copy or --open, or edit and post yourself.[/dim]")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: Run the full suite + linters**

Run: `uv run pytest -v && uv run ruff check . && uv run pyright`
Expected: all tests pass, ruff clean, pyright no errors.

- [ ] **Step 6: Commit**

```bash
git add shiplog/cli.py tests/test_cli.py
git commit -m "feat: shiplog draft CLI (print/copy/open)"
```

---

### Task 10: Manual end-to-end smoke (real model, one run)

**Files:** none (manual verification).

- [ ] **Step 1: Add a real key**

Copy `.env.example` to `.env` (created in Task 11) and set `OPENROUTER_API_KEY`.

- [ ] **Step 2: Run against this very repo**

Run: `cd /Users/gupta/Downloads/Development/Projects/shiplog && uv run shiplog draft --n 3 --tone punchy --print`
Expected: a printed draft under 280 chars about the shiplog commits, no traceback.

- [ ] **Step 3: Verify copy + open paths manually**

Run: `uv run shiplog draft --n 3 --copy` then paste somewhere to confirm clipboard contents.
Run: `uv run shiplog draft --n 3 --open` and confirm X compose opens pre-filled.

- [ ] **Step 4: Note the result**

If the draft quality is weak, that is a prompt-tuning follow-up (edit `prompts/*.md`), not a code bug. No commit needed.

---

### Task 11: OSS hygiene + lean-repo check

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `.env.example`

- [ ] **Step 1: Write `.env.example`**

`.env.example`:
```
# Required: get a key at https://openrouter.ai/keys
OPENROUTER_API_KEY=

# Optional overrides
# DEFAULT_MODEL=deepseek/deepseek-v4-flash
# DEFAULT_TONE=technical
```

- [ ] **Step 2: Write `LICENSE` (MIT)**

`LICENSE`:
```
MIT License

Copyright (c) 2026 Ayush Gupta

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 3: Write `README.md`**

`README.md`:
```markdown
# shiplog

Turn your git commits into a creative build-in-public X post. No push is too
small to share.

```bash
uv tool install shiplog        # or: clone + `uv sync`
export OPENROUTER_API_KEY=...   # https://openrouter.ai/keys
shiplog draft --since "1 day ago" --tone punchy
```

`shiplog` reads your recent local commits (and their diffs), understands what
you actually built, and drafts a post in your voice. You edit it and post it
yourself — nothing is auto-published.

## Usage

```bash
shiplog draft                 # last commits, default voice, interactive
shiplog draft --n 3 --copy    # last 3 commits, copy draft to clipboard
shiplog draft --open          # open X's compose window pre-filled
shiplog draft --tone funny    # technical | narrative | punchy | funny
shiplog draft --prompt ./my-voice.md   # bring your own prompt
```

Optional: drop a few of your real posts (one per line) in `~/.shiplog/voice.txt`
and shiplog will match your voice.

## Make it yours

The "creativity" is just markdown. Edit any file in `shiplog/prompts/`, or pass
your own with `--prompt`. That is the whole point — fork the voice without
touching code.

## How it works

`git log` (+ diffs) → a voice prompt you control → one structured LLM call via
[OpenRouter](https://openrouter.ai) → a draft you approve. No database, no
GitHub API, no auto-posting.

## License

MIT.
```

- [ ] **Step 4: Run the lean-repo + quality gate**

Run:
```bash
cd /Users/gupta/Downloads/Development/Projects/shiplog
uv run pytest -q
uv run ruff check .
uv run pyright
git status --porcelain
```
Expected: all tests pass; ruff + pyright clean. Confirm no stray files, no ported Supabase/Composio/asyncpg/Next.js artifacts, and `pyproject.toml` lists only the deps actually imported (typer, rich, openai, pydantic, pydantic-settings, pyperclip).

- [ ] **Step 5: Commit**

```bash
git add README.md LICENSE .env.example
git commit -m "docs: README, LICENSE, env example for OSS release"
```

---

## Self-Review

**Spec coverage:**
- Zero-config CLI + local git (no GitHub API/Composio) → Tasks 5, 9 ✓
- One engine, thin frontends (`core.draft_post`) → Task 8 ✓
- Single structured LLM call, no agent loop → Tasks 4, 7 ✓
- Default `deepseek/deepseek-v4-flash`, configurable → Tasks 2, 8, 9 ✓
- Voice = presets + user prompt file + few-shot examples, hackable → Task 6 ✓
- Draft → clipboard/browser, human posts → Task 9 ✓
- Error handling (not-a-repo, no commits, missing key, LLM failure, diff cap) → Tasks 4, 5, 9 ✓
- Tests with LLM mocked, 80%+ → every task is TDD; LLM always mocked ✓
- OSS hygiene (MIT, README, .env.example, `[project.scripts]`) → Tasks 1, 11 ✓
- Lean repo / no dead deps → Task 11 Step 4 ✓
- Out of scope (DB/auth/web/X API/scheduling/threads) → not built ✓
- Skill (v2) / MCP (v3) → documented in spec, not in this plan ✓

**Placeholder scan:** No TBD/TODO; every code step contains complete code; every command has expected output. ✓

**Type consistency:** `CommitContext`, `DraftPayload`, `PostDraft`, `chat_structured`, `read_commits`, `build_system_prompt`, `generate_draft`, `draft_post` signatures match across Tasks 3–9. `LLMResult.usage.total` used consistently. `GitError`/`VoiceError` raised where caught (Task 9). ✓
```
