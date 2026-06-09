# shippost v2 — End-of-day Reminder + Storytelling Presets

**Date:** 2026-06-10
**Status:** Approved design, pending spec review
**Builds on:** v1 (`core.draft_post` engine + CLI), spec `2026-06-09-shippost-design.md`

## Scope

Two additive changes over v1. MCP server (the originally-planned v3) is **dropped**.

1. **Storytelling presets** — make generated posts read like a human telling a
   small story with a soft, varied close, instead of a tool reporting changes.
2. **`shippost remind`** — an OS-level scheduler that, at a time you choose,
   drafts a post from *today's* commits, copies it to your clipboard, and fires
   a desktop notification. Silent when there are no commits.

Plus a shared enabler: a `--repo PATH` option so both the reminder (runs from a
fixed dir) and the `draft` command can target a repo other than the cwd.

## 1. Shared enabler — `--repo PATH`

`core.draft_post` already accepts `repo_path`. Expose it on the CLI `draft`
command as `--repo PATH` (default = current directory, unchanged behavior). The
reminder passes the repo it was installed for.

## 2. Storytelling presets (content)

Every post should follow a **micro story arc that fits in 280 chars**: a hook or
the moment → the friction/tension (what was hard, the snag, why it mattered) →
what actually shipped → a **soft, varied close**. The close is often a genuine
question or invitation, sometimes just a clean landing — **never** a templated
CTA ("follow for more", "drop a like", "🚀").

This is implemented by revising the four existing presets in
`shippost/prompts/*.md` (they stay standalone + hackable — editing one markdown
file remains the way to change the voice). Each preset keeps its distinct voice
and the existing hard anti-AI rules (no em dashes, no marketing words, no
"X? caught. Y? caught." parallelism), and gains a **Structure** section:

- **narrative** — leans into the full arc; a journal entry you happen to post.
- **technical** — the arc told dryly; tension = the actual bug/constraint.
- **punchy** — compressed arc: hook → the ship → a sharp soft close.
- **funny** — the arc with the joke coming from a real, specific detail.

The soft-CTA guidance lives in each preset's Structure section so it varies by
voice. No change to `draft.py` (structure stays in the hackable prompts, one
source of truth).

**Acceptance:** a generated post tells a tiny story (not a changelog line) and
ends naturally; across several runs the closes vary and none is a canned CTA.
(Verified by manual demo, since output is model-dependent; tests cover the
prompt-assembly plumbing, not the model's prose.)

## 3. `shippost remind` (OS reminder)

### Behavior (A1 + B1)

`shippost remind run` (what the scheduler invokes):
1. Read commits **since the start of today** in the target repo.
2. If none → exit silently (no nag).
3. If some → `core.draft_post(...)`, copy the body to the clipboard, and send a
   desktop notification: `"shippost — draft ready for N commits today (copied)"`.
4. If `--open` was configured at install time, also open X's compose window.
5. On failure (no key / offline / LLM error) → send a notification with the
   error instead of crashing silently, so a background failure is visible.

Notifications use **built-ins, no new dependencies**: `osascript` on macOS,
`notify-send` on Linux. (Not click-to-act; not needed since the draft is already
on the clipboard.)

### Scheduling

- **macOS (primary):** `remind install` writes a launchd agent to
  `~/Library/LaunchAgents/com.shippost.remind.plist` with a
  `StartCalendarInterval` (hour/minute), `WorkingDirectory` = the target repo
  (so it finds the repo's `.env` / `OPENROUTER_API_KEY`, since launchd does not
  inherit your shell environment), and `ProgramArguments` invoking
  `shippost remind run`. It then loads the agent via `launchctl`.
- **Linux (secondary):** `remind install` prints the crontab line to add
  manually (it does not auto-edit your crontab). `remind run` + notifications
  still work.
- **Windows:** unsupported in v2 (documented).

### Commands

- `shippost remind install --at HH:MM --repo PATH [--tone T] [--model M] [--open]`
- `shippost remind uninstall`
- `shippost remind status`
- `shippost remind run` (invoked by the scheduler; usable manually to test)

## Components / file layout

```
shippost/
  cli.py          # + `--repo` on draft; mount a `remind` Typer sub-app
  remind.py       # `remind` sub-app commands + run_reminder() logic
  notify.py       # send_notification(title, message) — osascript / notify-send
  schedule.py     # plist/crontab generation + install/uninstall/status
  ...             # core/git_reader/voice/draft/llm/models unchanged
  prompts/*.md    # revised: + Structure (story arc + soft CTA)
tests/
  test_notify.py      # platform dispatch + subprocess args (mocked)
  test_schedule.py    # plist/crontab content is correct (pure-ish, subprocess mocked)
  test_remind.py      # run_reminder: no-commits→no-notify; commits→draft+clipboard+notify
  test_cli.py         # + --repo forwards to draft_post; remind subcommands wired
```

## Error handling

- `remind run`: never crash the scheduled job; catch engine/LLM errors and
  surface them as a notification.
- `remind install` on non-macOS/Linux: clear message that auto-install is
  macOS-only, print the cron line for Linux.
- Missing `OPENROUTER_API_KEY` in the launchd env: the engine's existing clear
  RuntimeError is caught by `run_reminder` and shown as a notification.

## Testing (target 80%+, LLM + subprocess always mocked)

- `notify.py`: assert the right command/args per platform (monkeypatch
  `sys.platform` + capture subprocess args).
- `schedule.py`: assert generated plist XML / crontab line contains the right
  time, repo WorkingDirectory, and `remind run` args. Subprocess (launchctl)
  mocked.
- `remind.py`: mock `draft_post`, `pyperclip`, and `notify`; assert no
  notification when there are no commits, and draft→clipboard→notify when there
  are; assert errors become a notification.
- `cli.py`: `--repo` is forwarded to `draft_post`; `remind` subcommands exist.

## Out of scope (v2)

- MCP server (dropped).
- A conversational Claude Code Skill (dropped; CLI + reminder cover the flow).
- Clickable/action-button notifications (terminal-notifier).
- Linux auto-managed crontab (print-only) and Windows scheduling.
- X API auto-posting (unchanged from v1: human still posts).

## Build order

1. `--repo` enabler (small, unblocks the rest).
2. Storytelling presets (lands the content win early; testable plumbing only).
3. `notify.py` → `schedule.py` → `remind.py` → CLI wiring.
