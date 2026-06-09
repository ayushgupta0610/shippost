# shiplog

Turn your git commits into a creative build-in-public X post. No push is too small to share.

```bash
uv tool install shiplog        # or: clone + `uv sync`
export OPENROUTER_API_KEY=...   # https://openrouter.ai/keys
shiplog draft --since "1 day ago" --tone punchy --open
```

`shiplog` reads your recent local commits (and their diffs), understands what
you actually built, and drafts a post in your voice. You edit it and post it
yourself — nothing is auto-published.

## Usage

```bash
shiplog draft --open          # draft, then open X's compose window pre-filled (1 click to post)
shiplog draft --n 3 --copy    # last 3 commits, copy draft to clipboard
shiplog draft                 # last commits, default voice (prints draft + hints)
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
