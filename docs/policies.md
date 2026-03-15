# coauthorcheck policies

This page explains the policy settings supported by `coauthorcheck` and how they differ from rules.

## Rules vs policies

`coauthorcheck` uses two configuration layers:

- rules decide what is reported as an issue
- policies decide how those rules behave, or when validation should be skipped

Examples:

- `invalid_format` is a rule because it defines a trailer defect
- `name_parts` is a rule because it reports a name-part issue
- `minimum_name_parts` is a policy because it changes the threshold used by `name_parts`
- `ignore_bots` is a policy because it can skip validation entirely for certain commits or coauthors

Configuration locations:

- `pyproject.toml` under `[tool.coauthorcheck.policy]`
- `.coauthorcheck.toml` under `[policy]`

Example:

```toml
[tool.coauthorcheck.rules]
name_parts = "warning"
email_domain = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 3
allowed_email_domains = ["example.com"]
blocked_email_domains = ["users.noreply.github.com"]
allow_github_noreply = false
ignore_bots = true
```

## minimum_name_parts

Controls the minimum number of words required by the `name_parts` rule.

Default:

```toml
minimum_name_parts = 2
```

Examples:

```toml
[policy]
minimum_name_parts = 1
```

- allows single-word names such as `Prince`

```toml
[policy]
minimum_name_parts = 3
```

- requires names such as `Jane Doe Smith`

This policy only has an effect when the `name_parts` rule is enabled.

## allowed_email_domains

Defines a list of allowed email domains for the `email_domain` rule.

Example:

```toml
[policy]
allowed_email_domains = ["example.com", "company.com"]
```

Behavior:

- emails from listed domains pass
- emails from other domains produce `email-domain`
- if exactly one allowed domain is configured, `coauthorcheck` can suggest a corrected email address using that domain

## blocked_email_domains

Defines a list of forbidden email domains for the `email_domain` rule.

Example:

```toml
[policy]
blocked_email_domains = ["users.noreply.github.com", "tempmail.com"]
```

Behavior:

- emails from blocked domains produce `email-domain`
- this can be used without an allowlist
- if you also configure one allowed domain, `coauthorcheck` can suggest moving from a blocked domain to that allowed domain

## allow_github_noreply

Explicitly allows or disallows GitHub noreply addresses such as:

```text
12345+user@users.noreply.github.com
```

Example:

```toml
[policy]
allow_github_noreply = true
```

Behavior:

- `true`: GitHub noreply addresses are accepted
- `false`: GitHub noreply addresses produce `email-domain`

This is useful because many teams want a specific decision on GitHub noreply usage rather than relying only on generic domain allowlists or blocklists.

## ignore_bots

Skips validation for commits authored by bot accounts and for bot-style `Co-authored-by` names.

Example:

```toml
[policy]
ignore_bots = true
```

Behavior:

- skips commits authored by accounts such as `dependabot[bot]`
- skips bot-style coauthor names such as `dependabot[bot]`
- useful in automation-heavy repositories

This policy changes whether validation is applied at all, which is why it is a policy rather than a rule.

## email_domain policy requirements

The `email_domain` rule requires at least one of these policies:

- `allowed_email_domains`
- `blocked_email_domains`
- `allow_github_noreply`

If `email_domain` is enabled without any of them, configuration loading fails with an error.
