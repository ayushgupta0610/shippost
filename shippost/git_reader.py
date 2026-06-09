"""Read local git history via subprocess. No GitHub API, no auth."""

import subprocess
from datetime import datetime
from pathlib import Path

from shippost.models import CommitContext

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


def _full_diff(repo: Path, sha: str) -> str:
    return _run_git(repo, "show", "--no-color", "--stat", "--patch", "--format=", sha)


def read_commits(
    *,
    since: str | None = None,
    n: int | None = None,
    repo_path: Path | None = None,
    max_total_diff_chars: int = 6000,
) -> list[CommitContext]:
    """Return commits newest-first. `since` is any git date expr; `n` caps count.

    Diff text is bounded by `max_total_diff_chars` ACROSS all commits (not per
    commit): newest commits get the budget first, older ones are truncated to
    fit. This keeps the prompt small and generation fast.
    """
    repo = repo_path or Path.cwd()

    args = ["log", f"--pretty=format:{_FORMAT}"]
    if since:
        args.append(f"--since={since}")
    if n is not None:
        args.append(f"-n{n}")

    raw = _run_git(repo, *args)
    records = [r for r in raw.split(_RS) if r.strip()]
    if not records:
        raise GitError("No commits found for the given range.")

    commits: list[CommitContext] = []
    remaining = max_total_diff_chars
    for record in records:
        parts = (record.strip().split(_FS) + ["", "", "", "", ""])[:5]
        sha, author, iso, subject, body = parts

        full_diff = _full_diff(repo, sha)
        if remaining <= 0:
            diff_summary, truncated = "", True
        elif len(full_diff) > remaining:
            diff_summary, truncated = full_diff[:remaining], True
        else:
            diff_summary, truncated = full_diff, False
        remaining -= len(diff_summary)

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
