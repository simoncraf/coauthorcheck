from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CommitMessage:
    source: str
    message: str


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
    suggestion: str | None = None


@dataclass(slots=True)
class ValidationResult:
    source: str
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues
