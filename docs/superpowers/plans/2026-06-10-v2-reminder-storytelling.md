# shippost v2 (Reminder + Storytelling) Implementation Plan

> **For agentic workers:** Executed inline by the author with TDD. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add an end-of-day OS reminder that auto-drafts a post from today's commits, plus rewrite the voice presets to tell a micro-story with a soft, varied CTA. Add a `--repo` enabler.

**Architecture:** New thin modules over the v1 engine — `notify` (desktop notification), `schedule` (launchd/cron config), `remind` (the `remind` CLI sub-app + `run_reminder` logic). Presets are content-only edits. Voice-file loading is centralized in `voice.py`.

**Tech Stack:** Python 3.13, Typer, rich, pyperclip, stdlib subprocess (osascript/notify-send/launchctl). No new deps.

---

## File structure

```
shippost/
  voice.py        # + load_voice_examples() (centralized; cli + remind reuse)
  notify.py       # NEW: send_notification(title, message) — never raises
  schedule.py     # NEW: build_plist / build_cron_line (pure) + install/uninstall/status (launchd)
  remind.py       # NEW: run_reminder() + a Typer `remind` sub-app (install/uninstall/status/run)
  cli.py          # + --repo on draft; use voice.load_voice_examples(); mount remind sub-app
  prompts/*.md    # rewritten: micro-story arc + soft varied CTA, per-tone
tests/
  test_notify.py
  test_schedule.py
  test_remind.py
  test_cli.py     # + --repo forwarding; remind subcommands present
  test_voice.py   # + load_voice_examples()
```

**Type/interface contract (keep exact):**
- `voice.load_voice_examples() -> list[str]` (reads `~/.shippost/voice.txt`)
- `notify.send_notification(title: str, message: str) -> None`
- `schedule.build_plist(*, hour, minute, repo: Path, tone, model, open_x, program=None) -> str`
- `schedule.build_cron_line(*, hour, minute, repo, tone, model, open_x, program=None) -> str`
- `schedule.install_launchd(plist_content: str) -> Path` / `uninstall_launchd() -> bool` / `launchd_status() -> dict`
- `remind.run_reminder(*, repo: Path | None, tone, model, open_x) -> str` (returns "ok" | "no-commits" | "error")
- `remind.remind_app` (Typer) mounted at `app.add_typer(remind_app, name="remind")`

---

### Task 1: `--repo` enabler + centralize voice loading

- [ ] Add `load_voice_examples()` + `VOICE_FILE` to `voice.py`; test in `test_voice.py` (tmp file → lines; missing → []).
- [ ] In `cli.py`, replace local `_load_voice_examples`/`_VOICE_FILE` with `voice.load_voice_examples`; add `--repo PATH` option to `draft`, forward as `repo_path=repo` to `draft_post`.
- [ ] Test in `test_cli.py`: `--repo /x` is forwarded to `draft_post` (mock engine, capture kwargs).
- [ ] Gate + commit.

### Task 2: Storytelling presets

- [ ] Rewrite `prompts/{technical,narrative,punchy,funny}.md`: add a **Structure** section (hook → friction → ship → soft varied close), keep existing hard anti-AI rules, keep the test-asserted substrings (`precise, technical` in technical; `self-deprecating` in funny).
- [ ] `test_voice.py` still green (substrings preserved). Gate + commit.

### Task 3: `notify.py`

- [ ] Test (`test_notify.py`): monkeypatch `sys.platform`="darwin" → `osascript` called with a `display notification` arg containing the message; "linux" → `notify-send` called with title+message; missing binary (FileNotFoundError) → no raise.
- [ ] Implement `send_notification` (try/except, capture_output, never raises). Gate + commit.

### Task 4: `schedule.py`

- [ ] Test (`test_schedule.py`): `build_plist(hour=18, minute=0, repo=Path('/r'), tone='punchy', model=None, open_x=True, program='/bin/shippost')` contains `<integer>18</integer>`, `<integer>0</integer>`, `/r`, `remind`, `run`, `--open`, `--tone`, `punchy`, and the `com.shippost.remind` label. `build_cron_line(...)` → `0 18 * * * ... remind run --repo /r --tone punchy --open`. `install_launchd` writes the file and calls `launchctl load` (subprocess mocked); `uninstall_launchd` removes it.
- [ ] Implement. Gate + commit.

### Task 5: `remind.py` (logic + sub-app)

- [ ] Test (`test_remind.py`): mock `remind.draft_post`, `remind.notify.send_notification`, `remind.pyperclip`.
  - commits present → returns "ok", clipboard set to body, notification sent.
  - `draft_post` raises `GitError("No commits found ...")` → returns "no-commits", **no** notification.
  - `draft_post` raises `RuntimeError("OPENROUTER_API_KEY ...")` → returns "error", notification sent with the message.
- [ ] Implement `run_reminder` (since = today 00:00; GitError "No commits" → silent; other errors → notify). Build the `remind_app` Typer with `install/uninstall/status/run`.
- [ ] Gate + commit.

### Task 6: CLI wiring + final gate

- [ ] In `cli.py`: `from shippost.remind import remind_app`; `app.add_typer(remind_app, name="remind")`.
- [ ] Test (`test_cli.py`): `shippost remind --help` lists install/uninstall/status/run; `shippost remind run` with `run_reminder` mocked exits 0.
- [ ] Full gate: `uv run pytest -q && uv run ruff check . && uv run pyright`. Smoke `uv run shippost remind status` and `uv run shippost remind install --at 18:00 --repo . --print`-equivalent (dry path). Commit.

---

## Self-Review

**Spec coverage:** `--repo` (T1) ✓; storytelling presets (T2) ✓; notify built-ins (T3) ✓; launchd/cron schedule (T4) ✓; run_reminder A1 behavior incl. no-commits-silent + error-notify (T5) ✓; CLI `remind` group (T6) ✓; centralized voice loading (T1) ✓. Out-of-scope (MCP/Skill/Windows/clickable) correctly absent.
**Placeholders:** none — each task names exact files, functions, and test assertions.
**Type consistency:** `run_reminder`, `send_notification`, `build_plist/build_cron_line`, `load_voice_examples`, `remind_app` names consistent across tasks and the contract block.
