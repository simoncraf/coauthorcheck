# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

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
