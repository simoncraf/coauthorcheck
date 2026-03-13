from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Sequence

import click
import typer
from rich.console import Console
from rich.table import Table

from coauthorcheck.config import ConfigError, load_config
from coauthorcheck.git_utils import GitError, clean_commit_message_text, read_commit_message, read_commit_range
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


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


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
        return [
            CommitMessage(
                source=str(file_path),
                message=clean_commit_message_text(file_path.read_text(encoding="utf-8")),
            )
        ]

    if commit is not None:
        return [read_commit_message(commit)]

    if commit_range is not None:
        return read_commit_range(commit_range)

    if input_value is None:
        raise ValueError("One input source is required.")

    detected_kind = detect_input_kind(input_value)
    if detected_kind == "file":
        path = Path(input_value)
        return [
            CommitMessage(
                source=str(path),
                message=clean_commit_message_text(path.read_text(encoding="utf-8")),
            )
        ]
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


def _serialize_results(results: list[ValidationResult]) -> dict:
    commit_count = len(results)
    invalid_count = sum(not result.is_valid for result in results)
    issue_count = sum(len(result.issues) for result in results)
    status = "pass" if invalid_count == 0 else "fail"
    return {
        "status": status,
        "summary": {
            "commit_count": commit_count,
            "invalid_commit_count": invalid_count,
            "issue_count": issue_count,
        },
        "results": [
            {
                "source": result.source,
                "is_valid": result.is_valid,
                "issue_count": len(result.issues),
                "issues": [
                    {
                        "code": issue.code,
                        "message": issue.message,
                        "line_number": issue.line_number,
                    }
                    for issue in result.issues
                ],
            }
            for result in results
        ],
    }


def render_json(results: list[ValidationResult]) -> None:
    console.print_json(data=_serialize_results(results))


def _fail(message: str, output_format: OutputFormat = OutputFormat.TEXT, hint: str | None = None) -> None:
    if output_format == OutputFormat.JSON:
        payload = {
            "status": "error",
            "error": {
                "message": message,
            },
        }
        if hint is not None:
            payload["error"]["hint"] = hint
        console.print_json(data=payload)
        raise typer.Exit(code=2)

    error_console.print(f"[red]error:[/red] {message}")
    if hint is not None:
        error_console.print(f"hint: {hint}")
    raise typer.Exit(code=2)


def _fail_git_error(error: GitError, output_format: OutputFormat) -> None:
    _fail(error.message, output_format=output_format, hint=error.hint)


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
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Path to a configuration file. Supports .coauthorcheck.toml or pyproject.toml.",
        ),
    ] = None,
    output_format: Annotated[
        OutputFormat,
        typer.Option(
            "--format",
            help="Output format for validation results.",
            case_sensitive=False,
        ),
    ] = OutputFormat.TEXT,
) -> None:
    try:
        config = load_config(config_path=config_path)
        messages = load_messages(input_value, file_path, commit, commit_range)
    except ConfigError as error:
        _fail(str(error), output_format=output_format)
    except ValueError as error:
        _fail(str(error), output_format=output_format)
    except FileNotFoundError as error:
        _fail(f"file not found: {error.filename}", output_format=output_format)
    except GitError as error:
        _fail_git_error(error, output_format=output_format)
    except OSError as error:
        _fail(f"unable to read input: {error}", output_format=output_format)

    results = [validate_message(message.source, message.message, config=config) for message in messages]

    if output_format == OutputFormat.JSON:
        render_json(results)
    else:
        for result in results:
            render_result(result)

        render_summary(results)

    if any(not result.is_valid for result in results):
        raise typer.Exit(code=1)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = app(args=list(argv) if argv is not None else None, standalone_mode=False)
    except (typer.Exit, click.exceptions.Exit) as error:
        return int(error.exit_code)
    return int(result) if isinstance(result, int) else 0
