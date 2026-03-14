from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when configuration cannot be parsed."""


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


def _normalize_rule_value(value: object) -> Severity | None:
    if value is None:
        return None
    if value is True:
        return Severity.ERROR
    if value is False:
        return None
    if isinstance(value, Severity):
        return value
    if isinstance(value, str):
        normalized = value.lower()
        if normalized == Severity.ERROR:
            return Severity.ERROR
        if normalized == Severity.WARNING:
            return Severity.WARNING
    raise ValueError(f"Invalid rule value: {value!r}")


@dataclass(slots=True)
class RuleConfig:
    github_handle: Severity | bool | str | None = Severity.ERROR
    incorrect_casing: Severity | bool | str | None = Severity.ERROR
    invalid_format: Severity | bool | str | None = Severity.ERROR
    malformed_email: Severity | bool | str | None = Severity.ERROR
    missing_email: Severity | bool | str | None = Severity.ERROR
    missing_name: Severity | bool | str | None = Severity.ERROR
    name_parts: Severity | bool | str | None = Severity.ERROR
    email_domain: Severity | bool | str | None = None

    def __post_init__(self) -> None:
        for field in fields(type(self)):
            normalized = _normalize_rule_value(getattr(self, field.name))
            setattr(self, field.name, normalized)

    def severity_for(self, rule_name: str) -> Severity | None:
        return getattr(self, rule_name)


@dataclass(slots=True)
class Config:
    rules: RuleConfig
    allowed_email_domains: tuple[str, ...] = ()
    blocked_email_domains: tuple[str, ...] = ()
    minimum_name_parts: int = 2


DEFAULT_CONFIG = Config(rules=RuleConfig())


def load_config(config_path: Path | None = None, start_dir: Path | None = None) -> Config:
    if config_path is not None:
        return _load_config_file(config_path)

    for directory in _iter_search_dirs(start_dir or Path.cwd()):
        dedicated_path = directory / ".coauthorcheck.toml"
        if dedicated_path.is_file():
            return _load_config_file(dedicated_path)

        pyproject_path = directory / "pyproject.toml"
        if pyproject_path.is_file():
            return _load_config_file(pyproject_path)

    return Config(rules=RuleConfig())


def _iter_search_dirs(start_dir: Path) -> list[Path]:
    resolved = start_dir.resolve()
    return [resolved, *resolved.parents]


def _load_config_file(path: Path) -> Config:
    resolved = path.resolve()
    data = tomllib.loads(resolved.read_text(encoding="utf-8"))

    if resolved.name == "pyproject.toml":
        config_data = data.get("tool", {}).get("coauthorcheck", {})
    else:
        config_data = data

    return _parse_config(config_data, resolved)


def _parse_config(data: dict, path: Path) -> Config:
    if not isinstance(data, dict):
        raise ConfigError(f"Invalid configuration in {path}.")

    rules_data = data.get("rules", {})
    if not isinstance(rules_data, dict):
        raise ConfigError(f"'rules' must be a table in {path}.")

    policy_data = data.get("policy", {})
    if not isinstance(policy_data, dict):
        raise ConfigError(f"'policy' must be a table in {path}.")

    allowed_rule_names = {field.name for field in fields(RuleConfig)}
    unknown_rule_names = sorted(set(rules_data) - allowed_rule_names)
    if unknown_rule_names:
        names = ", ".join(unknown_rule_names)
        raise ConfigError(f"Unknown rule setting(s) in {path}: {names}.")

    rule_values: dict[str, bool | str] = {}
    for name, value in rules_data.items():
        if not isinstance(value, (bool, str)):
            raise ConfigError(
                f"Rule setting '{name}' in {path} must be a boolean or one of: 'error', 'warning'."
            )
        if isinstance(value, str) and value.lower() not in {Severity.ERROR, Severity.WARNING}:
            raise ConfigError(
                f"Rule setting '{name}' in {path} must be a boolean or one of: 'error', 'warning'."
            )
        rule_values[name] = value

    try:
        allowed_email_domains = policy_data.get("allowed_email_domains", [])
        if not isinstance(allowed_email_domains, list):
            raise ConfigError(f"'policy.allowed_email_domains' in {path} must be an array of strings.")
        blocked_email_domains = policy_data.get("blocked_email_domains", [])
        if not isinstance(blocked_email_domains, list):
            raise ConfigError(f"'policy.blocked_email_domains' in {path} must be an array of strings.")

        normalized_domains: list[str] = []
        for domain in allowed_email_domains:
            if not isinstance(domain, str) or not domain.strip():
                raise ConfigError(f"'policy.allowed_email_domains' in {path} must contain non-empty strings.")
            normalized_domains.append(domain.strip().lower())

        normalized_blocked_domains: list[str] = []
        for domain in blocked_email_domains:
            if not isinstance(domain, str) or not domain.strip():
                raise ConfigError(f"'policy.blocked_email_domains' in {path} must contain non-empty strings.")
            normalized_blocked_domains.append(domain.strip().lower())

        minimum_name_parts = policy_data.get("minimum_name_parts", 2)
        if not isinstance(minimum_name_parts, int) or isinstance(minimum_name_parts, bool):
            raise ConfigError(f"'policy.minimum_name_parts' in {path} must be an integer.")
        if minimum_name_parts < 1:
            raise ConfigError(f"'policy.minimum_name_parts' in {path} must be greater than or equal to 1.")

        if (normalized_domains or normalized_blocked_domains) and "email_domain" not in rule_values:
            rule_values["email_domain"] = Severity.ERROR

        email_domain_severity = _normalize_rule_value(rule_values.get("email_domain"))
        if email_domain_severity is not None and not normalized_domains and not normalized_blocked_domains:
            raise ConfigError(
                f"'rules.email_domain' in {path} requires 'policy.allowed_email_domains' or "
                f"'policy.blocked_email_domains' to be set."
            )

        return Config(
            rules=RuleConfig(**rule_values),
            allowed_email_domains=tuple(normalized_domains),
            blocked_email_domains=tuple(normalized_blocked_domains),
            minimum_name_parts=minimum_name_parts,
        )
    except ValueError as error:
        raise ConfigError(f"Invalid configuration in {path}: {error}") from error
