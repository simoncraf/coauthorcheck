# Integrations

This page shows how to use `coauthorcheck` in local hooks and GitHub Actions workflows.

## pre-commit

If you want to run `coauthorcheck` through `pre-commit`, you can either reference this repository directly or use a local hook.

### Option 1: Remote hook

Add this to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/simoncraf/coauthorcheck
    rev: v0.1.0
    hooks:
      - id: coauthorcheck
        stages: [commit-msg]
```

This validates the commit message being created.

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

## GitHub Actions

The most common CI usage is validating the commits introduced by a branch or pull request.

### Validate commits introduced by a pull request

Example:

```yaml
name: Validate Co-authored-by trailers

on:
  pull_request:

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
        run: pip install coauthorcheck

      - name: Validate PR commits
        run: coauthorcheck "${{ github.event.pull_request.base.sha }}..${{ github.event.pull_request.head.sha }}"
```

### Validate commits introduced by a branch push

Example:

```yaml
name: Validate Co-authored-by trailers

on:
  push:
    branches:
      - main
      - master
      - "feature/**"

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
        run: pip install coauthorcheck

      - name: Validate commits in branch range
        run: coauthorcheck "origin/main..HEAD"
```

Adjust the base branch if your repository does not use `main`.

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

## Future Integration Work

Future releases are expected to add machine-readable output and richer pull request feedback, which will make automated PR comments easier to implement.
