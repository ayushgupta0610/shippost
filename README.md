# shippost

Turn your git commits into a creative build-in-public X post. No push is too small to share.

```bash
git clone https://github.com/ayushgupta0610/shippost.git
cd shippost && uv sync
export OPENROUTER_API_KEY=...   # https://openrouter.ai/keys
uv run shippost draft --since "1 day ago" --tone punchy --open
```

`shippost` reads your recent local commits (and their diffs), understands what
you actually built, and drafts a post in your voice. You edit it and post it
yourself. Nothing is auto-published.

## Usage

Until it is on PyPI, run from the cloned repo with `uv run shippost <args>`
(the examples below drop the `uv run` for brevity):

```bash
shippost draft --open          # draft, then open X's compose window pre-filled (1 click to post)
shippost draft --n 3 --copy    # last 3 commits, copy draft to clipboard
shippost draft                 # last 5 commits, default voice (prints draft + hints)
shippost draft --tone funny    # technical | narrative | punchy | funny
shippost draft --prompt ./my-voice.md   # bring your own prompt
```

Optional: drop a few of your real posts (one per line) in `~/.shippost/voice.txt`
and shippost will match your voice.

## Make it yours

The "creativity" is just markdown. Edit any file in `shippost/prompts/`, or pass
your own with `--prompt`. That is the whole point: fork the voice without
touching code.

## How it works

`git log` (+ diffs) → a voice prompt you control → one structured LLM call via
[OpenRouter](https://openrouter.ai) → a draft you approve. No database, no
GitHub API, no auto-posting.

## License

MIT.
