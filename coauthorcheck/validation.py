from __future__ import annotations

import re

from coauthorcheck.config import Config, DEFAULT_CONFIG
from coauthorcheck.models import Trailer, ValidationIssue, ValidationResult
from coauthorcheck.parser import extract_coauthor_trailers

COAUTHOR_TOKEN = "Co-authored-by"
NAME_EMAIL_PATTERN = re.compile(r"^(?P<name>.*?)\s*<(?P<email>[^<>]+)>$")
EMAIL_PATTERN = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
GITHUB_HANDLE_PATTERN = re.compile(r"^@[A-Za-z0-9-]+$")


def _build_issue(code: str, message: str, line_number: int) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, line_number=line_number)


def validate_trailer(trailer: Trailer, config: Config = DEFAULT_CONFIG) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    match = NAME_EMAIL_PATTERN.match(trailer.value)

    if config.rules.incorrect_casing and trailer.token != COAUTHOR_TOKEN:
        issues.append(
            _build_issue(
                "incorrect-casing",
                f"Trailer token should be '{COAUTHOR_TOKEN}'.",
                trailer.line_number,
            )
        )

    if match is None:
        if config.rules.invalid_format:
            issues.append(
                _build_issue(
                    "invalid-format",
                    "Trailer must use the format 'Co-authored-by: Full Name <email@example.com>'.",
                    trailer.line_number,
                )
            )

        if config.rules.missing_email and ("<" not in trailer.value or ">" not in trailer.value):
            issues.append(
                _build_issue(
                    "missing-email",
                    "Trailer is missing an email address in angle brackets.",
                    trailer.line_number,
                )
            )

        if config.rules.missing_name and (
            trailer.value.startswith("<") or not trailer.value.split("<", 1)[0].strip()
        ):
            issues.append(
                _build_issue(
                    "missing-name",
                    "Trailer is missing the author name before the email address.",
                    trailer.line_number,
                )
            )

        return _dedupe_issues(issues)

    name = match.group("name").strip()
    email = match.group("email").strip()

    if not name:
        if config.rules.missing_name:
            issues.append(
                _build_issue(
                    "missing-name",
                    "Trailer is missing the author name before the email address.",
                    trailer.line_number,
                )
            )
        if config.rules.invalid_format:
            issues.append(
                _build_issue(
                    "invalid-format",
                    "Trailer must use the format 'Co-authored-by: Full Name <email@example.com>'.",
                    trailer.line_number,
                )
            )
    elif config.rules.github_handle and GITHUB_HANDLE_PATTERN.match(name):
        issues.append(
            _build_issue(
                "github-handle",
                "Use a real name instead of a GitHub handle in the trailer.",
                trailer.line_number,
            )
        )
    elif config.rules.single_word_name and len(name.split()) == 1:
        issues.append(
            _build_issue(
                "single-word-name",
                "Author name should contain at least two words.",
                trailer.line_number,
            )
        )

    if config.rules.missing_email and not email:
        issues.append(
            _build_issue(
                "missing-email",
                "Trailer is missing an email address in angle brackets.",
                trailer.line_number,
            )
        )
    elif config.rules.malformed_email and not EMAIL_PATTERN.match(email):
        issues.append(
            _build_issue(
                "malformed-email",
                "Email address is malformed.",
                trailer.line_number,
            )
        )

    return _dedupe_issues(issues)


def validate_message(source: str, message: str, config: Config = DEFAULT_CONFIG) -> ValidationResult:
    issues: list[ValidationIssue] = []

    for trailer in extract_coauthor_trailers(message):
        issues.extend(validate_trailer(trailer, config=config))

    return ValidationResult(source=source, issues=_dedupe_issues(issues))


def _dedupe_issues(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    seen: set[tuple[str, int]] = set()
    deduped: list[ValidationIssue] = []

    for issue in issues:
        key = (issue.code, issue.line_number)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)

    return deduped
