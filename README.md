<p align="center">
  <img src="docs/assets/coauthorcheck.png" alt="coauthorcheck logo" width="180">
</p>

<h1 align="center">coauthorcheck</h1>

<p align="center">Lightweight command-line validation for <code>Co-authored-by</code> commit trailers.</p>

<p align="center">
  <a href="https://github.com/simoncraf/coauthorcheck/actions/workflows/ci.yml">
    <img src="https://github.com/simoncraf/coauthorcheck/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/coauthorcheck/">
    <img src="https://img.shields.io/pypi/v/coauthorcheck" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/coauthorcheck/">
    <img src="https://img.shields.io/pypi/pyversions/coauthorcheck" alt="Supported Python versions">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/pypi/l/coauthorcheck" alt="License">
  </a>
</p>

## Table of Contents

- [Usage](#usage)
- [pre-commit](#pre-commit)
- [GitHub Actions](#github-actions)
- [CLI](#cli)
- [Installation](#installation)
- [Common CLI Workflows](#common-cli-workflows)
- [Configuration](#configuration)
- [Development](#development)

## Usage

`coauthorcheck` works in any Git repository, regardless of the project's language or build system.
You can use `coauthorcheck` in one of these three ways:

- as a `pre-commit` `commit-msg` hook for immediate local feedback
- in GitHub Actions to validate branch or pull request commits before merge
- directly from CLI


### pre-commit

Add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/simoncraf/coauthorcheck
    rev: v0.5.0
    hooks:
      - id: coauthorcheck
        stages: [commit-msg]
```

Then install the hook:

```bash
pre-commit install --hook-type commit-msg
```

This is required because `coauthorcheck` validates the final commit message file, and `commit-msg` is the Git hook that receives that file.

### GitHub Actions

The easiest GitHub integration is the reusable composite action:

```yaml
- uses: simoncraf/coauthorcheck-action@v0.2.0
  with:
    range: origin/main..HEAD
```

You can also install it from GitHub Marketplace:
[coauthorcheck Marketplace Action](https://github.com/marketplace/actions/coauthorcheck)

Validate commits introduced by branch pushes:

```yaml
name: Validate Co-authored-by trailers

on:
  push:
    branches:
      - "feature/**"
      - "feat/**"

jobs:
  validate-commits:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Validate branch commits
        uses: simoncraf/coauthorcheck-action@v0.2.0
        with:
          range: origin/main..HEAD
```

Validate commits introduced by a pull request:

```yaml
name: Validate Co-authored-by trailers on PR

on:
  pull_request:
    branches:
      - main

jobs:
  validate-commits:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Validate PR commits
        uses: simoncraf/coauthorcheck-action@v0.2.0
        with:
          range: origin/${{ github.base_ref }}..HEAD
```

See [docs/integrations.md](docs/integrations.md) for local hooks, JSON output, PR comments, and more workflow examples.

When validation fails, `coauthorcheck` also prints a suggested corrected trailer line. If multiple issues affect the same trailer, they are merged into one canonical fix suggestion.

### CLI

```bash
coauthorcheck .git/COMMIT_EDITMSG
coauthorcheck HEAD
coauthorcheck HEAD~5..HEAD
coauthorcheck main..HEAD
coauthorcheck origin/main..HEAD

coauthorcheck --file .git/COMMIT_EDITMSG
coauthorcheck --commit HEAD
coauthorcheck --range HEAD~5..HEAD
```

Positional input is auto-detected in this order:
- values containing `..` or `...` are treated as commit ranges
- existing paths are treated as commit message files
- everything else is treated as a commit ref

Use the explicit flags when you want fully unambiguous scripting.

Check the installed CLI:

```bash
coauthorcheck --help
```

## Installation

Install from PyPI:

```bash
pip install coauthorcheck
```

Or with `uv`:

```bash
uv tool install coauthorcheck
```

Or with `pipx`:

```bash
pipx install coauthorcheck
```

After installation, run:

```bash
coauthorcheck --help
```

## Common CLI Workflows

Validate the commit message currently being edited:

```bash
coauthorcheck .git/COMMIT_EDITMSG
```

Validate only the commits introduced by your current branch compared with `main`:

```bash
coauthorcheck main..HEAD
```

Validate only the commits introduced by your branch compared with the remote default branch:

```bash
coauthorcheck origin/main..HEAD
```

Validate the last few commits on the current branch:

```bash
coauthorcheck HEAD~3..HEAD
```

## Configuration

`coauthorcheck` supports repository-local configuration from either:

- `pyproject.toml` under `[tool.coauthorcheck]`
- `.coauthorcheck.toml`

Configuration is resolved in this order:

1. `--config <path>`
2. nearest `.coauthorcheck.toml`
3. nearest `pyproject.toml` with `[tool.coauthorcheck]`
4. built-in defaults

When config files are auto-discovered, `coauthorcheck` searches upward from the current working directory. This means running the tool from a nested folder in the repo still finds the repo-level config.

Example using `pyproject.toml`:

```toml
[tool.coauthorcheck.rules]
name_parts = "warning"
github_handle = "warning"
incorrect_casing = "error"
invalid_format = "error"
malformed_email = "error"
missing_email = "error"
missing_name = "error"
email_domain = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 2
allowed_email_domains = ["example.com"]
blocked_email_domains = ["users.noreply.github.com"]
allow_github_noreply = false
```

Example using `.coauthorcheck.toml`:

```toml
[rules]
name_parts = false
github_handle = "warning"
incorrect_casing = "error"
invalid_format = "error"
malformed_email = "error"
missing_email = "error"
missing_name = "error"
email_domain = "error"

[policy]
minimum_name_parts = 1
allowed_email_domains = ["example.com"]
blocked_email_domains = ["users.noreply.github.com"]
allow_github_noreply = true
```

Use an explicit config file with:

```bash
coauthorcheck --config .coauthorcheck.toml main..HEAD
```

Rule values can be:

- `false`: disable the rule
- `true` or `"error"`: enable the rule as an error
- `"warning"`: enable the rule as a warning

`email_domain` is a special policy rule. If you enable it, you must also configure `allowed_email_domains`, `blocked_email_domains`, `allow_github_noreply`, or a combination of them under `[tool.coauthorcheck.policy]` in `pyproject.toml` or under `[policy]` in `.coauthorcheck.toml`.

`name_parts` uses the `minimum_name_parts` policy value. The default is `2`, which preserves the current "first and last name" behavior. Set `minimum_name_parts = 1` to relax the rule, or a higher value such as `3` to require more name parts.

Example:

```toml
[tool.coauthorcheck.rules]
email_domain = "warning"
name_parts = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 3
allowed_email_domains = ["example.com", "company.com"]
blocked_email_domains = ["users.noreply.github.com"]
allow_github_noreply = false
```

With that configuration:

- co-author names must contain at least three parts
- emails from the listed domains are allowed
- emails from blocked domains are rejected
- GitHub noreply addresses are explicitly rejected
- emails from other domains produce an `email-domain` issue
- if exactly one allowed domain is configured, `coauthorcheck` can suggest a corrected email domain
- enabling `email_domain` without `allowed_email_domains`, `blocked_email_domains`, or `allow_github_noreply` is a configuration error

Only error-level issues fail the command with exit code `1`. Warnings are reported but do not fail the run.

Unknown rule names or invalid values are treated as configuration errors.

See [docs/rules.md](docs/rules.md) for a detailed explanation of each rule.
See [docs/integrations.md](docs/integrations.md) for `pre-commit`, GitHub Actions, JSON output, and PR comment examples.
Use `coauthorcheck --format json ...` for machine-readable output in CI and automation.
JSON issue objects also include a `suggestion` field when a corrected trailer can be proposed.

## Development

Set up the local environment:

```bash
uv sync
```

Run the CLI from the project environment:

```bash
uv run coauthorcheck --help
```

Run the tool from another repository by changing into that repository first and then invoking the executable from this project:

```bash
cd /path/to/other-repo
/path/to/coauthorcheck/.venv/Scripts/coauthorcheck.exe main..HEAD
```

In Git Bash, use `/c/...` style paths:

```bash
/path/to/coauthorcheck/.venv/Scripts/coauthorcheck.exe main..HEAD
```

Run the test suite:

```bash
uv run pytest
```

Run the linter:

```bash
uv run ruff check .
```
