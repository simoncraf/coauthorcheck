# coauthorcheck

Lightweight command-line validation for `Co-authored-by` commit trailers.

## Usage

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

## Common Workflows

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
single_word_name = false
github_handle = true
incorrect_casing = true
invalid_format = true
malformed_email = true
missing_email = true
missing_name = true
```

Example using `.coauthorcheck.toml`:

```toml
[rules]
single_word_name = false
github_handle = false
incorrect_casing = true
invalid_format = true
malformed_email = true
missing_email = true
missing_name = true
```

Use an explicit config file with:

```bash
coauthorcheck --config .coauthorcheck.toml main..HEAD
```

Unknown rule names or non-boolean values are treated as configuration errors.

See [RULES.md](RULES.md) for a detailed explanation of each rule.

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

## Local Development

For local development in this repo:

```bash
uv sync
```

Run from the project virtualenv:

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

## Development

Run the test suite:

```bash
uv run pytest
```

Run the linter:

```bash
uv run ruff check .
```

The command exits with `0` when all detected `Co-authored-by` trailers are valid, `1` when validation issues are found, and `2` when the input cannot be read.
