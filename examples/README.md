# Examples

This directory contains ready-to-copy integration examples for `coauthorcheck`.

## GitHub Actions

The `examples/github-actions/` folder shows three common ways to use the tool in pull request and branch workflows.

### `pr-validation.yml`

Use this when you want a simple failing check on pull requests.

What it does:

- checks out the full Git history
- uses the reusable `coauthorcheck` GitHub Action
- validates the commits introduced by the pull request using:
  - `origin/${{ github.base_ref }}..HEAD`
- fails the workflow if invalid trailers are found

Use this when:

- you only need a pass/fail signal
- you do not want workflow logic for comments or richer reporting
- you want a workflow you can narrow to a single test branch with `if: github.head_ref == 'your-branch'`

### `branch-validation.yml`

Use this when you want validation on branch pushes instead of only on pull requests.

What it does:

- checks out the repository with full history
- uses the reusable `coauthorcheck` GitHub Action
- validates the commits introduced by the current branch relative to `origin/main`

Use this when:

- your team wants validation on every push
- you want to enforce branch-level checks before review

Important:

- if your default branch is not `main`, adjust the range accordingly

### `pr-comment.yml`

Use this when you want both enforcement and reviewer-friendly feedback on pull requests.

What it does:

- installs `coauthorcheck` explicitly and captures JSON output
- runs `coauthorcheck --format json`
- captures the tool result in `result.json`
- posts a comment when invalid trailers are found
- updates the existing bot comment on reruns instead of creating duplicates
- removes the bot comment once validation passes again
- fails the workflow when validation issues are present

Use this when:

- you want contributors to see exactly what failed in the pull request itself
- you want automation that is more user-friendly than a simple failed check

Tradeoff:

- this workflow is more complex than the simple validation example because it includes PR comment management

## Choosing an Example

Start with:

- `pr-validation.yml` if you want the simplest CI enforcement

Move to:

- `pr-comment.yml` if you want richer pull request feedback

Use:

- `branch-validation.yml` if your team prefers validating pushes directly on branches

The validation examples are intentionally action-based. The PR comment example stays workflow-based because it needs extra JSON handling and GitHub comment logic around the raw CLI output.
