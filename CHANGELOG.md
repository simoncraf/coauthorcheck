# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.7.0] - 2026-03-16

### Added

- Stable JSON contract metadata with `schema_version` and `tool_version` in machine-readable output.

## [0.6.0] - 2026-03-15

### Added

- Rule severities with support for `error`, `warning`, and disabled rules.
- Policy controls for `minimum_name_parts`, `allowed_email_domains`, `blocked_email_domains`, `allow_github_noreply`, and `ignore_bots`.
- Dedicated policy documentation under `docs/policies.md`.
- End-to-end integration tests using temporary Git repositories and real commits.

### Changed

- Renamed the name validation rule from `single_word_name` to `name_parts`.
- Improved CI to install `pytest` explicitly and run unit and integration suites separately.
- Expanded README, rules, and integrations documentation to explain policy-driven configuration and bot/email-domain behavior.

## [0.5.0] - 2026-03-14

### Added

- Reusable composite GitHub Action for validating commit ranges with `coauthorcheck`.

### Changed

- Updated GitHub Actions examples to use the reusable action for pull request and branch validation.
- Expanded the integrations and examples documentation to describe the action inputs and usage.

## [0.4.0] - 2026-03-14

### Changed

- Improved validation messages to use more actionable remediation-oriented wording.
- Expanded suggested-fix documentation across the README, integrations guide, and rules reference.

## [0.3.0] - 2026-03-13

### Added

- Suggested fix output for invalid `Co-authored-by` trailers in both text and JSON modes.
- Merged trailer suggestions so multiple validation issues on one trailer point to a single corrected line.

### Changed

- Improved README and integration examples around `pre-commit`, GitHub Actions, installation, and common workflows.

## [0.2.1] - 2026-03-13

### Fixed

- Strip Git comment and help lines from commit message files before parsing trailers.
- Ensure invalid `Co-authored-by` trailers fail consistently in `commit-msg` hooks for editor-based `git commit` flows.

## [0.2.0] - 2026-03-13

### Added

- Machine-readable JSON output via `--format json` for CI and automation workflows.
- GitHub Actions example for pull request commenting driven by JSON output.
- Integration documentation for `pre-commit`, branch validation, pull request validation, and automation use cases.
- Example documentation under `examples/` to explain how each workflow example works and when to use it.
- Project README improvements including installation guidance, logo, and badges.

### Changed

- Improved pull request comment workflow behavior to update a single bot comment instead of creating duplicates.

## [0.1.0] - 2026-03-13

### Added

- Initial `coauthorcheck` CLI for validating `Co-authored-by` trailers from files, commits, and commit ranges.
- Trailer parsing limited to the final commit trailer block with case-insensitive `Co-authored-by` detection.
- Rule-based validation for casing, format, missing name, missing email, malformed email, GitHub handles, and single-word names.
- Rich CLI output with commit-level reporting, summaries, and exit codes.
- Repository-local configuration via `pyproject.toml`, `.coauthorcheck.toml`, and `--config`.
- Improved Git error guidance with actionable hints for common revision and repository failures.
- Test coverage for parser, validation, config loading, CLI behavior, and Git error interpretation.
- Project documentation for usage, configuration, and rule reference.
