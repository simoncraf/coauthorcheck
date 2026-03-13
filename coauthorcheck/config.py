from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
import tomllib


class ConfigError(ValueError):
    """Raised when configuration cannot be parsed."""


@dataclass(slots=True)
class RuleConfig:
    github_handle: bool = True
    incorrect_casing: bool = True
    invalid_format: bool = True
    malformed_email: bool = True
    missing_email: bool = True
    missing_name: bool = True
    single_word_name: bool = True


@dataclass(slots=True)
class Config:
    rules: RuleConfig


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

    allowed_rule_names = {field.name for field in fields(RuleConfig)}
    unknown_rule_names = sorted(set(rules_data) - allowed_rule_names)
    if unknown_rule_names:
        names = ", ".join(unknown_rule_names)
        raise ConfigError(f"Unknown rule setting(s) in {path}: {names}.")

    rule_values: dict[str, bool] = {}
    for name, value in rules_data.items():
        if not isinstance(value, bool):
            raise ConfigError(f"Rule setting '{name}' in {path} must be a boolean.")
        rule_values[name] = value

    return Config(rules=RuleConfig(**rule_values))
