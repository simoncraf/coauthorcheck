# Integrations

This page shows how to use `coauthorcheck` in local hooks and GitHub Actions workflows.

## pre-commit

If you want to run `coauthorcheck` through `pre-commit`, you can either reference this repository directly or use a local hook.

### Option 1: Remote hook

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/simoncraf/coauthorcheck
    rev: v0.5.0
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

### Reusable GitHub Action

`coauthorcheck` ships with a reusable composite action so other repositories can validate commits with a single `uses:` step.

Example:

```yaml
- uses: simoncraf/coauthorcheck/.github/actions/coauthorcheck@v0.5.0
  with:
    package-version: "0.5.0"
    range: origin/main..HEAD
```

Supported inputs:

- `range`: required git revision range to validate
- `package-version`: optional PyPI version to install; leave empty for the latest release
- `config`: optional config file path
- `format`: optional output format, `text` or `json`
- `python-version`: optional Python version used inside the action
- `working-directory`: optional working directory for running `coauthorcheck`

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

      - name: Validate PR commits
        uses: simoncraf/coauthorcheck/.github/actions/coauthorcheck@v0.5.0
        with:
          package-version: "0.5.0"
          range: origin/${{ github.base_ref }}..HEAD
```

If you want machine-readable output for later processing, use JSON:

```yaml
- name: Validate PR commits
  uses: simoncraf/coauthorcheck/.github/actions/coauthorcheck@v0.5.0
  with:
    package-version: "0.5.0"
    format: json
    range: origin/${{ github.base_ref }}..HEAD
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

      - name: Validate branch commits
        uses: simoncraf/coauthorcheck/.github/actions/coauthorcheck@v0.5.0
        with:
          package-version: "0.5.0"
          range: origin/main..HEAD
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
  - `suggestion`

When multiple issues affect the same trailer, `coauthorcheck` merges them into one canonical suggested trailer line. In text output that suggestion is shown once for the trailer; in JSON the related issues share the same `suggestion` value.

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

The PR comment workflow still calls the CLI directly instead of the reusable action because it needs access to the raw JSON file and custom comment-management logic.

## Future Integration Work

Future releases are expected to improve the reusable action further and may publish it in GitHub Marketplace once the action interface is stable.
