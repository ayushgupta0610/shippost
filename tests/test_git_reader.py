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


def test_since_filters_out_old_commits(repo: Path):
    # Nothing was committed in the future, so this range is empty -> GitError.
    with pytest.raises(GitError, match="No commits found"):
        read_commits(since="2099-01-01", repo_path=repo)


def test_no_commits_in_empty_repo(tmp_path: Path):
    _git(tmp_path, "init")
    with pytest.raises(GitError):
        read_commits(repo_path=tmp_path)


def test_not_a_git_repo(tmp_path: Path):
    with pytest.raises(GitError):
        read_commits(repo_path=tmp_path)
