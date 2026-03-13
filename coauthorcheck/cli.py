from __future__ import annotations

from pathlib import Path
from typing import Annotated, Sequence

import typer
from rich.console import Console
from rich.table import Table

from coauthorcheck.git_utils import GitError, read_commit_message, read_commit_range
from coauthorcheck.models import CommitMessage, ValidationResult
from coauthorcheck.validation import validate_message

app = typer.Typer(
    add_completion=False,
    help="Validate Co-authored-by trailers in commit messages.",
    no_args_is_help=False,
    pretty_exceptions_enable=False,
)
console = Console()
error_console = Console(stderr=True)


def load_messages(
    input_value: str | None,
    file_path: Path | None,
    commit: str | None,
    commit_range: str | None,
) -> list[CommitMessage]:
    explicit_values = [value for value in (file_path, commit, commit_range) if value is not None]
    if input_value and explicit_values:
        raise ValueError("Provide either a positional input or an explicit flag, not both.")

    if file_path is not None:
        return [CommitMessage(source=str(file_path), message=file_path.read_text(encoding="utf-8"))]

    if commit is not None:
        return [read_commit_message(commit)]

    if commit_range is not None:
        return read_commit_range(commit_range)

    if input_value is None:
        raise ValueError("One input source is required.")

    detected_kind = detect_input_kind(input_value)
    if detected_kind == "file":
        path = Path(input_value)
        return [CommitMessage(source=str(path), message=path.read_text(encoding="utf-8"))]
    if detected_kind == "range":
        return read_commit_range(input_value)
    return [read_commit_message(input_value)]


def detect_input_kind(value: str) -> str:
    if Path(value).exists():
        return "file"
    if ".." in value:
        return "range"
    return "commit"


def render_result(result: ValidationResult) -> None:
    if result.is_valid:
        console.print(f"[green]OK[/green] {result.source}")
        return

    console.print(f"[red]Issues[/red] {result.source} ({len(result.issues)})")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Line", style="cyan", justify="right", no_wrap=True)
    table.add_column("Code", style="magenta", no_wrap=True)
    table.add_column("Message", style="white")

    for issue in result.issues:
        table.add_row(str(issue.line_number), issue.code, issue.message)

    console.print(table)


def render_summary(results: list[ValidationResult]) -> None:
    commit_count = len(results)
    invalid_count = sum(not result.is_valid for result in results)
    issue_count = sum(len(result.issues) for result in results)
    status = "[green]PASS[/green]" if invalid_count == 0 else "[red]FAIL[/red]"
    console.print(
        f"Summary: {status} - checked {commit_count} commit(s), "
        f"{invalid_count} commit(s) with issues, {issue_count} total issue(s)"
    )


def _fail(message: str) -> None:
    error_console.print(f"[red]error:[/red] {message}")
    raise typer.Exit(code=2)


@app.command()
def run(
    input_value: Annotated[
        str | None,
        typer.Argument(
            help=(
                "Auto-detected input source: file path, commit ref, or commit range. "
                "Ranges are detected by '..' or '...'."
            ),
        ),
    ] = None,
    file_path: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Read a commit message from a file."),
    ] = None,
    commit: Annotated[
        str | None,
        typer.Option("--commit", "-c", help="Read a commit message from a commit hash or ref."),
    ] = None,
    commit_range: Annotated[
        str | None,
        typer.Option(
            "--range",
            "-r",
            help="Read commit messages from a git revision range, for example HEAD~5..HEAD.",
        ),
    ] = None,
) -> None:
    try:
        messages = load_messages(input_value, file_path, commit, commit_range)
    except ValueError as error:
        _fail(str(error))
    except FileNotFoundError as error:
        _fail(f"file not found: {error.filename}")
    except GitError as error:
        _fail(f"unable to read commit messages from git: {error}")
    except OSError as error:
        _fail(f"unable to read input: {error}")

    results = [validate_message(message.source, message.message) for message in messages]

    for result in results:
        render_result(result)

    render_summary(results)

    if any(not result.is_valid for result in results):
        raise typer.Exit(code=1)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        app(args=list(argv) if argv is not None else None, standalone_mode=False)
    except typer.Exit as error:
        return int(error.exit_code)
    return 0
