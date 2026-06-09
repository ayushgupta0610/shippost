# shiplog — Design Spec

**Date:** 2026-06-09
**Status:** Approved design, pending spec review
**Author:** Ayush (with Claude)

## One line

A zero-config CLI that turns your recent git commits (with diffs) into a
creative, voice-matched build-in-public X post you approve and post yourself.

## Why this exists

Developers want to build in public but stall on it — they hit a bug, lose the
thread, and the post never happens. `shiplog` removes the thinking: run one
command, get a genuinely good draft of "what I shipped today," edit it, post it.

It is open source so the *creativity itself* is hackable: the prompt that
controls voice and style is a plain file the user owns and edits.

### Where it sits in the learning roadmap

This is the shippable form of "project one" (the `ship_log` learning repo, which
covered FastAPI + LLM + a handwritten ReAct agent + SSE). `shiplog` reuses that
project's LLM layer and ports the useful Pydantic models into a clean,
dependency-light package. The Supabase/Composio/Next.js parts of the learning
repo are intentionally left behind.

## Landscape / why build vs buy

A June 2026 scan found the space splits into two camps, neither of which is this:

- **AI commit-*message* generators** (OpenCommit, Gritch, claude-git) — they
  write `git commit -m`, not public posts.
- **General social-post generators** (URL→post, langchain social-media-agent) —
  heavy, SaaS-shaped, not a zero-config dev CLI.
- **Auto-tweet-your-commit** plugins (lolcommits-twitter) — gimmicky, low quality.

Unowned gap: a zero-config CLI that reads local commits **and diffs**,
understands what was actually built, and drafts a creative, voice-matched post
with a **fully hackable creativity prompt**. That gap is the wedge.

## Architecture: one engine, thin frontends

The core is a pure library function. Every distribution channel is a thin
adapter over it — no logic is duplicated across channels.

```
        shiplog.core.draft_post(repo, since, n, tone, prompt, model) -> PostDraft
        /                 |                    \
   CLI adapter        Skill adapter         MCP adapter
   (v1, this spec)    (v2, planned)         (v3, planned)
```

### v1 package layout

```
shiplog/
  core.py          # draft_post(...) — the engine; the only public API
  git_reader.py    # subprocess over `git log` / `git show` -> CommitContext[]
  voice.py         # load preset + user prompt template + voice examples -> system prompt
  draft.py         # build messages -> chat_structured -> PostDraft
  llm/             # ported from ship_log: OpenRouter client + chat helpers
  models.py        # CommitContext, PostDraft (Pydantic v2, frozen, extra=forbid)
  config.py        # pydantic-settings (.env: OPENROUTER_API_KEY) + defaults
  cli.py           # Typer app: `shiplog draft ...` + interactive review loop
  prompts/         # shipped presets: technical.md, narrative.md, punchy.md, funny.md
docs/superpowers/specs/   # this spec
tests/
README.md  LICENSE (MIT)  .env.example  pyproject.toml
```

## Data flow (v1)

```
shiplog draft --since "1 day ago" --tone punchy
  1. git_reader : git log + truncated diffs           -> [CommitContext]
  2. voice      : preset/template (+ past-tweet anchors) -> system prompt
  3. draft      : chat_structured(commits, voice, model) -> PostDraft (body + 2 alt variants)
  4. cli (rich) : render draft -> [r]egenerate · [e]dit · [c]opy · [o]pen X · [q]uit
  5. output     : copy to clipboard OR open https://x.com/intent/tweet?text=...
                  (user hits Post themselves — human stays in the loop)
```

`draft_post` does steps 1–3 and returns a `PostDraft`. The CLI owns step 4–5
(interaction + side effects). Skill/MCP adapters reuse steps 1–3 and present
results their own way.

## Components

### `git_reader.py`
- Pure functions wrapping `git` via `subprocess` (no GitHub API, no auth).
- `read_commits(since: str | None, n: int | None) -> list[CommitContext]`.
- Pulls subject, body, author, timestamp, changed files, and a **truncated**
  diff per commit (cap total diff chars; note when truncated).
- Errors: not a git repo, no commits in range — raise typed errors with
  friendly messages.

### `voice.py`
- `build_system_prompt(tone: str | None, prompt_path: Path | None, voice_examples: list[str]) -> str`.
- Resolution order: explicit `--prompt FILE` > `--tone` preset from `prompts/`
  > default preset (`technical`).
- Optional `~/.shiplog/voice.txt` (a few of the user's real posts) injected as
  few-shot voice anchors.
- **This file + `prompts/*.md` are the hackable heart**: forking "how creative
  it gets" means editing one markdown file, no code.

### `draft.py` + `llm/`
- Reuse ported `chat_structured` (OpenAI SDK pointed at OpenRouter).
- Single structured LLM call (no agent/tool loop in v1 — YAGNI; commits→post is
  one generation, not a tool-using loop). Returns `PostDraft`.
- Default model: `deepseek/deepseek-v4-flash` (verified real OpenRouter slug,
  2026-06-09). Configurable via `--model` / config.

### `models.py`
- `CommitContext` (frozen): sha, message, author, committed_at, files_changed,
  diff_summary, diff_truncated: bool.
- `PostDraft` (frozen): body, char_count, variants: list[str], model_used.

### `cli.py`
- Typer app. Command: `shiplog draft`.
- Flags: `--since`, `--n`, `--tone`, `--prompt`, `--model`, and output mode
  (`--copy` / `--open` / `--print`; interactive default).
- Interactive review loop via `rich`: regenerate / edit-in-place / copy / open
  X compose / quit.

### `config.py`
- `pydantic-settings`; only place that reads env. `OPENROUTER_API_KEY` required;
  clear error if missing. Default model + default tone live here.

## Error handling

Fail fast, friendly messages (per coding-style rules):
- Not a git repository.
- No commits in the requested range.
- Missing `OPENROUTER_API_KEY`.
- LLM timeout / network error → one retry, then a clear message.
- Diff exceeds size cap → truncate and tell the model (and the user) it happened.

## Testing (target 80%+)

`pytest`. **The LLM is always mocked — no real API calls in tests.**
- `git_reader`: parse against a temporary fixture git repo (real `git init` +
  commits in a tmp dir).
- `voice`: prompt-assembly + resolution order; one golden-prompt test.
- `models`: validation / immutability.
- `cli`: command wiring with the engine mocked (Typer's `CliRunner`).

## Stack

Python 3.13, `uv`, `ruff`, `pyright`, `pytest`. Runtime deps: `typer`, `rich`,
`openai` (OpenRouter transport), `pydantic` + `pydantic-settings`, `pyperclip`
(clipboard; fall back to native `pbcopy`/`xclip` if needed).

## OSS hygiene

- `[project.scripts] shiplog = "shiplog.cli:app"`.
- MIT LICENSE.
- README with a 60-second quickstart (`uv tool install` / clone, set one key, run).
- `.env.example`.
- CONTRIBUTING note: "to change the voice, edit `prompts/*.md` or pass `--prompt`."
- Verify the `shiplog` name is free on PyPI before publishing (not yet checked).

## Out of scope for v1 (YAGNI)

No DB, no auth, no web app, no GitHub API / Composio, no X API auto-posting, no
scheduling, no thread generation, no LinkedIn, no agent/tool loop.

## Planned later phases (documented, not built now)

- **v2 — Skill + end-of-day reminder.** A `SKILL.md` that calls
  `shiplog.core.draft_post` (or shells the CLI) for Claude Code users, plus a
  scheduled trigger. Note: a skill cannot self-trigger — the reminder is a
  separate scheduling layer (a `/schedule` routine or a `Stop`/cron hook that
  fires the skill at ~18:00 with the day's commits). Ship the skill *and* a
  recommended schedule snippet together.
- **v3 — MCP server.** Thin wrapper exposing a `draft_post` tool to any MCP
  client (Cursor, Claude Desktop). Optional hosted version later for true
  zero-install (adds hosting cost/ops).

## Open decisions resolved

- New clean repo `shiplog/`, not in-place evolution of the learning repo. ✓
- Drop the ReAct agent loop for v1 (single structured call). ✓
- Typer for the CLI. ✓
- Draft → clipboard/browser; no X API in v1. ✓
- Voice = editable prompt file + presets + optional few-shot examples. ✓
- Default model `deepseek/deepseek-v4-flash`, configurable. ✓
- Build engine + CLI now; spec Skill (v2) and MCP (v3) as future phases. ✓
```
