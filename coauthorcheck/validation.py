from __future__ import annotations

import re

from coauthorcheck.config import Config, DEFAULT_CONFIG, Severity
from coauthorcheck.models import Trailer, ValidationIssue, ValidationResult
from coauthorcheck.parser import extract_coauthor_trailers

COAUTHOR_TOKEN = "Co-authored-by"
NAME_EMAIL_PATTERN = re.compile(r"^(?P<name>.*?)\s*<(?P<email>[^<>]+)>$")
EMAIL_PATTERN = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")
GITHUB_HANDLE_PATTERN = re.compile(r"^@[A-Za-z0-9-]+$")
EMBEDDED_EMAIL_PATTERN = re.compile(r"(?P<email>[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+)$")


def _build_issue(
    code: str,
    message: str,
    line_number: int,
    severity: Severity,
    suggestion: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        line_number=line_number,
        severity=severity,
        suggestion=suggestion,
    )


def _suggested_trailer(name: str | None = None, email: str | None = None) -> str:
    suggested_name = name.strip() if name and name.strip() else "Full Name"
    suggested_email = email.strip() if email and email.strip() else "email@example.com"
    return f"{COAUTHOR_TOKEN}: {suggested_name} <{suggested_email}>"


def _extract_trailer_parts(trailer: Trailer) -> tuple[str | None, str | None]:
    match = NAME_EMAIL_PATTERN.match(trailer.value)
    if match is not None:
        name = match.group("name").strip() or None
        email = match.group("email").strip() or None
        return name, email

    raw_value = trailer.value.strip()
    name_part, separator, email_part = raw_value.partition("<")
    if separator:
        name = name_part.strip() or None
        email = email_part.replace(">", "").strip() or None
        return name, email

    embedded_email = EMBEDDED_EMAIL_PATTERN.search(raw_value)
    if embedded_email is not None:
        email = embedded_email.group("email").strip()
        name = raw_value[: embedded_email.start()].strip() or None
        return name, email

    return raw_value or None, None


def _merged_suggestion(trailer: Trailer, issue_codes: set[str]) -> str:
    name, email = _extract_trailer_parts(trailer)

    if "missing-name" in issue_codes or not name:
        name = "Full Name"
    elif "github-handle" in issue_codes:
        name = "Full Name"
    elif "single-word-name" in issue_codes:
        name = f"{name} Surname"

    if ("missing-email" in issue_codes and not email) or not email:
        email = "email@example.com"
    elif "malformed-email" in issue_codes:
        email = "email@example.com"

    return _suggested_trailer(name=name, email=email)


def _apply_suggestion(issues: list[ValidationIssue], trailer: Trailer) -> list[ValidationIssue]:
    if not issues:
        return issues

    suggestion = _merged_suggestion(trailer, {issue.code for issue in issues})
    for issue in issues:
        issue.suggestion = suggestion
    return issues


def validate_trailer(trailer: Trailer, config: Config = DEFAULT_CONFIG) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    match = NAME_EMAIL_PATTERN.match(trailer.value)

    severity = config.rules.severity_for("incorrect_casing")
    if severity and trailer.token != COAUTHOR_TOKEN:
        issues.append(
            _build_issue(
                "incorrect-casing",
                f"Use the exact trailer token '{COAUTHOR_TOKEN}'.",
                trailer.line_number,
                severity=severity,
            )
        )

    if match is None:
        severity = config.rules.severity_for("invalid_format")
        if severity:
            issues.append(
                _build_issue(
                    "invalid-format",
                    "Trailer must use the format 'Co-authored-by: Full Name <email@example.com>'.",
                    trailer.line_number,
                    severity=severity,
                )
            )

        severity = config.rules.severity_for("missing_email")
        if severity and ("<" not in trailer.value or ">" not in trailer.value):
            issues.append(
                _build_issue(
                    "missing-email",
                    "Add an email address in angle brackets, for example <email@example.com>.",
                    trailer.line_number,
                    severity=severity,
                )
            )

        severity = config.rules.severity_for("missing_name")
        if severity and (
            trailer.value.startswith("<") or not trailer.value.split("<", 1)[0].strip()
        ):
            issues.append(
                _build_issue(
                    "missing-name",
                    "Add the author name before the email address.",
                    trailer.line_number,
                    severity=severity,
                )
            )

        return _apply_suggestion(_dedupe_issues(issues), trailer)

    name = match.group("name").strip()
    email = match.group("email").strip()

    if not name:
        severity = config.rules.severity_for("missing_name")
        if severity:
            issues.append(
                _build_issue(
                    "missing-name",
                    "Add the author name before the email address.",
                    trailer.line_number,
                    severity=severity,
                )
            )
        severity = config.rules.severity_for("invalid_format")
        if severity:
            issues.append(
                _build_issue(
                    "invalid-format",
                    "Trailer must use the format 'Co-authored-by: Full Name <email@example.com>'.",
                    trailer.line_number,
                    severity=severity,
                )
            )
    else:
        severity = config.rules.severity_for("github_handle")
        if severity and GITHUB_HANDLE_PATTERN.match(name):
            issues.append(
                _build_issue(
                    "github-handle",
                    "Use a full name instead of a GitHub handle in the trailer.",
                    trailer.line_number,
                    severity=severity,
                )
            )
        else:
            severity = config.rules.severity_for("single_word_name")
            if severity and len(name.split()) == 1:
                issues.append(
                    _build_issue(
                        "single-word-name",
                        "Use at least a first and last name in the trailer.",
                        trailer.line_number,
                        severity=severity,
                    )
                )

    severity = config.rules.severity_for("missing_email")
    if severity and not email:
        issues.append(
            _build_issue(
                "missing-email",
                "Add an email address in angle brackets, for example <email@example.com>.",
                trailer.line_number,
                severity=severity,
            )
        )
    else:
        severity = config.rules.severity_for("malformed_email")
        if severity and not EMAIL_PATTERN.match(email):
            issues.append(
                _build_issue(
                    "malformed-email",
                    "Use a valid email address in angle brackets.",
                    trailer.line_number,
                    severity=severity,
                )
            )

    return _apply_suggestion(_dedupe_issues(issues), trailer)


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
