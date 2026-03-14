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
GITHUB_NOREPLY_DOMAINS = {"users.noreply.github.com", "noreply.github.com"}


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


def _merged_suggestion(trailer: Trailer, issue_codes: set[str], config: Config) -> str:
    name, email = _extract_trailer_parts(trailer)

    if "missing-name" in issue_codes or not name:
        name = "Full Name"
    elif "github-handle" in issue_codes:
        name = "Full Name"
    elif "name-parts" in issue_codes:
        current_parts = name.split() if name else []
        while len(current_parts) < config.minimum_name_parts:
            current_parts.append("Surname")
        name = " ".join(current_parts)

    if ("missing-email" in issue_codes and not email) or not email:
        email = "email@example.com"
    elif "malformed-email" in issue_codes:
        email = "email@example.com"
    elif "email-domain" in issue_codes:
        suggested_email = _suggest_email_for_allowed_domain(email, config.allowed_email_domains)
        if suggested_email is not None:
            email = suggested_email

    return _suggested_trailer(name=name, email=email)


def _suggest_email_for_allowed_domain(
    email: str | None,
    allowed_domains: tuple[str, ...],
) -> str | None:
    if not allowed_domains:
        return None

    local_part = "user"
    if email and "@" in email:
        candidate = email.split("@", 1)[0].strip()
        if candidate:
            local_part = candidate

    if len(allowed_domains) == 1:
        return f"{local_part}@{allowed_domains[0]}"

    return None


def _email_domain_issue(name: str, email: str, line_number: int, config: Config) -> ValidationIssue:
    suggestion = None
    suggested_email = _suggest_email_for_allowed_domain(email, config.allowed_email_domains)
    if suggested_email is not None:
        suggestion = _suggested_trailer(name=name, email=suggested_email)

    return _build_issue(
        "email-domain",
        "Use an email address from an allowed, non-blocked domain.",
        line_number,
        severity=config.rules.severity_for("email_domain"),
        suggestion=suggestion,
    )


def _is_github_noreply_domain(domain: str) -> bool:
    return domain in GITHUB_NOREPLY_DOMAINS


def _apply_suggestion(issues: list[ValidationIssue], trailer: Trailer, config: Config) -> list[ValidationIssue]:
    if not issues:
        return issues

    if not any(issue.suggestion for issue in issues):
        issue_codes = {issue.code for issue in issues}
        if issue_codes == {"email-domain"} and _suggest_email_for_allowed_domain(
            _extract_trailer_parts(trailer)[1],
            config.allowed_email_domains,
        ) is None:
            return issues

    suggestion = _merged_suggestion(trailer, {issue.code for issue in issues}, config)
    for issue in issues:
        issue.suggestion = suggestion
    return issues


def _name_part_issue(config: Config, line_number: int) -> ValidationIssue:
    minimum_name_parts = config.minimum_name_parts
    code = "name-parts"
    if minimum_name_parts == 2:
        message = "Use at least a first and last name in the trailer."
    else:
        message = f"Use at least {minimum_name_parts} name parts in the trailer."
    return _build_issue(
        code,
        message,
        line_number,
        severity=config.rules.severity_for("name_parts"),
    )


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

        return _apply_suggestion(_dedupe_issues(issues), trailer, config)

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
            severity = config.rules.severity_for("name_parts")
            if severity and len(name.split()) < config.minimum_name_parts:
                issues.append(_name_part_issue(config, trailer.line_number))

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
        else:
            severity = config.rules.severity_for("email_domain")
            if severity and (
                config.allowed_email_domains
                or config.blocked_email_domains
                or config.allow_github_noreply is not None
            ):
                domain = email.rsplit("@", 1)[1].lower()
                is_github_noreply = _is_github_noreply_domain(domain)
                if is_github_noreply and config.allow_github_noreply is True:
                    violates_allowed_domains = False
                    violates_blocked_domains = False
                    violates_github_noreply = False
                else:
                    violates_allowed_domains = bool(
                        config.allowed_email_domains and domain not in config.allowed_email_domains
                    )
                    violates_blocked_domains = domain in config.blocked_email_domains
                    violates_github_noreply = is_github_noreply and config.allow_github_noreply is False
                if violates_allowed_domains or violates_blocked_domains or violates_github_noreply:
                    issues.append(_email_domain_issue(name, email, trailer.line_number, config))

    return _apply_suggestion(_dedupe_issues(issues), trailer, config)


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
