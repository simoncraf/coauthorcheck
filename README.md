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

## Installation

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
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The command exits with `0` when all detected `Co-authored-by` trailers are valid, `1` when validation issues are found, and `2` when the input cannot be read.
