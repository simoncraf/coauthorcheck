# Integrations

This page shows how to use `coauthorcheck` in local hooks and GitHub Actions workflows.

## pre-commit

If you want to run `coauthorcheck` through `pre-commit`, you can either reference this repository directly or use a local hook.

### Option 1: Remote hook

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/simoncraf/coauthorcheck
    rev: v0.3.0
    hooks:
      - id: coauthorcheck
        stages: [commit-msg]
```

This validates the commit message being created.

Install the hook with:

```bash
pre-commit install --hook-type commit-msg
```

The `commit-msg` hook type is required here. A normal `pre-commit install` is not enough on its own.
This is necessary because `coauthorcheck` validates the final commit message file, and `commit-msg` is the Git hook that receives that file.

### Option 2: Local hook

If `coauthorcheck` is already installed in your environment, use a local hook:

```yaml
repos:
  - repo: local
    hooks:
      - id: coauthorcheck
        name: coauthorcheck
        entry: coauthorcheck
        language: system
        stages: [commit-msg]
```

Use `language: system` only if your environment already provides the `coauthorcheck` command.

Install the hook with:

```bash
pre-commit install --hook-type commit-msg
```

In both examples above, `pre-commit` passes the commit message file path automatically to the hook.
This is why `commit-msg` is the correct hook type for commit message validation.

## GitHub Actions

The most common CI usage is validating the commits introduced by a branch or pull request.

### Validate commits introduced by a pull request

Example:

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

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install coauthorcheck
        run: pip install coauthorcheck==0.3.0

      - name: Validate PR commits
        run: coauthorcheck "origin/${{ github.base_ref }}..HEAD"
```

If you want machine-readable output for later processing, use JSON:

```yaml
- name: Validate PR commits
  run: coauthorcheck --format json "${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }}"
```

### Validate commits introduced by a branch push

Example:

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

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install coauthorcheck
        run: pip install coauthorcheck==0.3.0

      - name: Validate branch commits
        run: coauthorcheck "origin/main..HEAD"
```

Adjust the base branch if your repository does not use `main`.

For temporary testing on a single pull request branch, gate the job with a branch condition:

```yaml
jobs:
  validate-commits:
    if: github.head_ref == 'feature/coauthorcheck-test-pr'
```

## Recommended CI Ranges

Use these patterns:

- `main..HEAD`: validate commits introduced by the current branch
- `origin/main..HEAD`: validate against the fetched remote base branch
- `${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }}`: validate commits in a PR

Avoid using fixed slices like `HEAD~5..HEAD` in CI unless that is explicitly what you want.

## Configuration In Hooks And CI

If your repository uses configuration, `coauthorcheck` will auto-discover:

- `.coauthorcheck.toml`
- `pyproject.toml` under `[tool.coauthorcheck]`

You can also pass an explicit config file:

```yaml
- name: Validate commits
  run: coauthorcheck --config .coauthorcheck.toml origin/main..HEAD
```

## Exit Codes

In hooks and CI:

- `0`: validation passed
- `1`: validation issues were found
- `2`: execution, Git, or configuration error

## JSON Output

Use `--format json` when another tool or workflow needs structured results:

```bash
coauthorcheck --format json main..HEAD
```

Output shape:

```json
{
  "status": "pass",
  "summary": {
    "commit_count": 1,
    "invalid_commit_count": 0,
    "issue_count": 0
  },
  "results": [
    {
      "source": "abc123",
      "is_valid": true,
      "issue_count": 0,
      "issues": []
    }
  ]
}
```

When validation issues are found:

- `status` becomes `"fail"`
- `invalid_commit_count` is greater than `0`
- each invalid result includes an `issues` list with:
  - `code`
  - `message`
  - `line_number`

When execution fails, `coauthorcheck` emits an error payload:

```json
{
  "status": "error",
  "error": {
    "message": "current directory is not a git repository.",
    "hint": "Run this command inside a Git repository, or pass a commit message file path instead."
  }
}
```

## Pull Request Commenting

JSON output makes it possible to comment on pull requests with a workflow script.

See [examples/github-actions/pr-comment.yml](../examples/github-actions/pr-comment.yml) for a complete example that:

- runs `coauthorcheck --format json`
- fails when invalid trailers are found
- upserts a single pull request comment summarizing the failures
- removes the previous bot comment again once validation passes

## Future Integration Work

Future releases are expected to add machine-readable output and richer pull request feedback, which will make automated PR comments easier to implement.
