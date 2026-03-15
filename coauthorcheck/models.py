from __future__ import annotations

from dataclasses import dataclass, field

from coauthorcheck.config import Severity


@dataclass(slots=True)
class CommitMessage:
    source: str
    message: str
    author_name: str | None = None
    author_email: str | None = None


@dataclass(slots=True)
class Trailer:
    token: str
    value: str
    raw: str
    line_number: int


@dataclass(slots=True)
class ValidationIssue:
    code: str
    message: str
    line_number: int
    severity: Severity = Severity.ERROR
    suggestion: str | None = None


@dataclass(slots=True)
class ValidationResult:
    source: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    @property
    def error_count(self) -> int:
        return sum(issue.severity == Severity.ERROR for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == Severity.WARNING for issue in self.issues)
