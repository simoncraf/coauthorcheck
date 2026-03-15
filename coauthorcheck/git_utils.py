from __future__ import annotations

import subprocess
from dataclasses import dataclass

from coauthorcheck.models import CommitMessage


@dataclass(slots=True)
class GitError(RuntimeError):
    """Raised when git cannot provide commit messages."""

    message: str
    hint: str | None = None
    raw_error: str | None = None

    def __str__(self) -> str:
        return self.message


def read_commit_message(commit: str) -> CommitMessage:
    return CommitMessage(
        source=commit,
        message=_run_git(["show", "-s", "--format=%B", commit]),
        author_name=_run_git(["show", "-s", "--format=%an", commit]).strip() or None,
        author_email=_run_git(["show", "-s", "--format=%ae", commit]).strip() or None,
    )


def read_commit_range(commit_range: str) -> list[CommitMessage]:
    output = _run_git(["rev-list", "--reverse", commit_range])
    commits = [line.strip() for line in output.splitlines() if line.strip()]
    return [read_commit_message(commit) for commit in commits]


def clean_commit_message_text(message: str, comment_char: str = "#") -> str:
    cleaned_lines: list[str] = []
    scissors_marker = f"{comment_char} ------------------------ >8 ------------------------"

    for line in message.splitlines():
        if line == scissors_marker:
            break
        if line.startswith(comment_char):
            continue
        cleaned_lines.append(line)

    cleaned_message = "\n".join(cleaned_lines).rstrip()
    if message.endswith("\n"):
        return f"{cleaned_message}\n" if cleaned_message else ""
    return cleaned_message


def _run_git(args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "git command failed"
        raise interpret_git_error(stderr, args)
    return completed.stdout


def interpret_git_error(stderr: str, args: list[str]) -> GitError:
    lowered = stderr.lower()
    revision = args[-1] if args else None

    if "not a git repository" in lowered:
        return GitError(
            message="current directory is not a git repository.",
            hint="Run this command inside a Git repository, or pass a commit message file path instead.",
            raw_error=stderr,
        )

    if "detected dubious ownership" in lowered or "safe.directory" in lowered:
        return GitError(
            message="git refused to read this repository because it is not marked as safe.",
            hint="Run 'git config --global --add safe.directory <repo-path>' for this repository.",
            raw_error=stderr,
        )

    if any(text in lowered for text in ("unknown revision", "bad revision", "ambiguous argument")):
        target = f" '{revision}'" if revision else ""
        if revision and ".." in revision:
            return GitError(
                message=f"unable to resolve revision range{target}.",
                hint=(
                    "Try a smaller range like 'HEAD~1..HEAD', or validate only commits introduced by "
                    "your branch with 'main..HEAD' or 'origin/main..HEAD'."
                ),
                raw_error=stderr,
            )

        return GitError(
            message=f"unable to resolve revision{target}.",
            hint="Check that the commit, branch, or tag exists in the current repository.",
            raw_error=stderr,
        )

    return GitError(
        message="git failed to read commit messages.",
        hint=stderr,
        raw_error=stderr,
    )
