# Integrations

This page shows how to use `coauthorcheck` in local hooks and GitHub Actions workflows.

## pre-commit

If you want to run `coauthorcheck` through `pre-commit`, you can either reference this repository directly or use a local hook.

### Option 1: Remote hook

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/simoncraf/coauthorcheck
    rev: v0.6.0
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
- uses: simoncraf/coauthorcheck-action@v0.2.0
  with:
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
        uses: simoncraf/coauthorcheck-action@v0.2.0
        with:
          range: origin/${{ github.base_ref }}..HEAD
```

If you want machine-readable output for later processing, use JSON:

```yaml
- name: Validate PR commits
  uses: simoncraf/coauthorcheck-action@v0.2.0
  with:
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
        uses: simoncraf/coauthorcheck-action@v0.2.0
        with:
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

Rule values may be set to `false`, `true`, `"error"`, or `"warning"`. Warning-level rules are reported in output but do not fail the command.

The `email_domain` rule is policy-driven and requires an allowed-domain list:

```toml
[tool.coauthorcheck.rules]
email_domain = "error"

[tool.coauthorcheck.policy]
allowed_email_domains = ["example.com"]
blocked_email_domains = ["users.noreply.github.com"]
allow_github_noreply = false
ignore_bots = true
```

You can use `allowed_email_domains`, `blocked_email_domains`, `allow_github_noreply`, or combine them. If `email_domain` is enabled without any of those policies, `coauthorcheck` exits with a configuration error.

`ignore_bots = true` skips validation for commits authored by bot accounts and for bot-style `Co-authored-by` names. This is useful when automation tools generate commit messages or coauthor trailers.

The `name_parts` rule is also policy-aware. It uses `minimum_name_parts`, which defaults to `2`:

```toml
[tool.coauthorcheck.rules]
name_parts = "warning"

[tool.coauthorcheck.policy]
minimum_name_parts = 3
```

With that configuration, names with fewer than three parts are reported, but only as warnings.

## Exit Codes

In hooks and CI:

- `0`: validation passed
- `1`: validation issues were found
- `2`: execution, Git, or configuration error

Only error-level issues trigger exit code `1`. Warning-only results still exit successfully.

## JSON Output

Use `--format json` when another tool or workflow needs structured results:

```bash
coauthorcheck --format json main..HEAD
```

Output shape:

```json
{
  "schema_version": 1,
  "tool_version": "0.6.0",
  "status": "pass",
  "summary": {
    "commit_count": 1,
    "invalid_commit_count": 0,
    "warning_commit_count": 0,
    "issue_count": 0,
    "error_count": 0,
    "warning_count": 0
  },
  "results": [
    {
      "source": "abc123",
      "is_valid": true,
      "issue_count": 0,
      "error_count": 0,
      "warning_count": 0,
      "issues": []
    }
  ]
}
```

Contract notes:

- `schema_version` is the JSON contract version intended for downstream automation such as the separate Marketplace action
- `tool_version` is the installed `coauthorcheck` package version
- action-side comment logic should treat this JSON output as the source of truth instead of parsing text output

When validation issues are found:

- `status` becomes `"fail"`
- `invalid_commit_count` is greater than `0`
- each invalid result includes an `issues` list with:
  - `code`
  - `message`
  - `line_number`
  - `severity`
  - `suggestion`

When multiple issues affect the same trailer, `coauthorcheck` merges them into one canonical suggested trailer line. In text output that suggestion is shown once for the trailer; in JSON the related issues share the same `suggestion` value.

If `email-domain` is triggered and exactly one allowed domain is configured, the suggestion also normalizes the email to that domain, even when the original domain was blocked.

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
