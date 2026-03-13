from __future__ import annotations

import subprocess

from coauthorcheck.models import CommitMessage


class GitError(RuntimeError):
    """Raised when git cannot provide commit messages."""


def read_commit_message(commit: str) -> CommitMessage:
    return CommitMessage(source=commit, message=_run_git(["show", "-s", "--format=%B", commit]))


def read_commit_range(commit_range: str) -> list[CommitMessage]:
    output = _run_git(["rev-list", "--reverse", commit_range])
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    return [read_commit_message(commit) for commit in commits]


def _run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "git command failed"
        raise GitError(stderr)
    return completed.stdout
