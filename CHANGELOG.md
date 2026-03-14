# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

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
