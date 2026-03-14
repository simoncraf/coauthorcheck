# coauthorcheck rules

This page explains each validation rule supported by `coauthorcheck`.

All rule ids can be configured in either:

- `pyproject.toml` under `[tool.coauthorcheck.rules]`
- `.coauthorcheck.toml` under `[rules]`

Example:

```toml
[tool.coauthorcheck.rules]
name_parts = "warning"
github_handle = "error"
email_domain = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 2
allowed_email_domains = ["example.com"]
blocked_email_domains = ["users.noreply.github.com"]
```

Each rule accepts one of these values:

- `false`: disable the rule
- `true` or `"error"`: enable the rule as an error
- `"warning"`: enable the rule as a warning

## incorrect_casing

Checks that the trailer token is exactly:

```text
Co-authored-by:
```

This rule reports an issue when the token is detected case-insensitively but the exact casing is different.

Examples:

```text
co-authored-by: Jane Doe <jane@example.com>
CO-AUTHORED-BY: Jane Doe <jane@example.com>
```

## invalid_format

Checks that the trailer value matches the expected structure:

```text
Full Name <email@example.com>
```

This rule reports an issue when the overall trailer format does not match the expected name-plus-angle-bracket-email shape.

Examples:

```text
Co-authored-by: Jane Doe jane@example.com
Co-authored-by: <jane@example.com>
```

## github_handle

Checks whether the name portion is a GitHub-style handle such as:

```text
@octocat
```

When enabled, the rule requires a real name instead of a handle.

Example:

```text
Co-authored-by: @octocat <octocat@example.com>
```

## name_parts

Checks whether the name contains only one word.

When enabled, the rule requires at least `minimum_name_parts` words in the co-author name.
If `minimum_name_parts` is not configured, the default is `2`.

Example:

```text
Co-authored-by: Prince <prince@example.com>
```

Policy examples:

```toml
[tool.coauthorcheck.rules]
name_parts = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 1
```

With `minimum_name_parts = 1`, a single-word name is allowed.

```toml
[tool.coauthorcheck.rules]
name_parts = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 3
```

With `minimum_name_parts = 3`, `Jane Doe <jane@example.com>` produces a `name-parts` issue.

## missing_name

Checks whether the trailer is missing the name before the email address.

Example:

```text
Co-authored-by: <jane@example.com>
```

## missing_email

Checks whether the trailer is missing an email address in angle brackets.

Examples:

```text
Co-authored-by: Jane Doe
Co-authored-by: Jane Doe jane@example.com
```

## malformed_email

Checks whether the email address exists but does not match the expected syntax.

Examples:

```text
Co-authored-by: Jane Doe <octocat>
Co-authored-by: Jane Doe <jane@@example.com>
```

## email_domain

Checks whether the email address belongs to an allowed domain and not to a blocked domain.

Example:

```text
Co-authored-by: Jane Doe <jane@other.com>
```

Configuration example:

```toml
[tool.coauthorcheck.rules]
email_domain = "error"

[tool.coauthorcheck.policy]
minimum_name_parts = 2
allowed_email_domains = ["example.com", "company.com"]
blocked_email_domains = ["users.noreply.github.com", "tempmail.com"]
```

How it works:

- if the trailer email uses one of the allowed domains, no issue is reported
- if the trailer email uses a blocked domain, `email-domain` is reported
- if the trailer email uses a different domain, `email-domain` is reported
- if exactly one allowed domain is configured, `coauthorcheck` can suggest a corrected email address using that domain
- if `email_domain` is enabled but both `allowed_email_domains` and `blocked_email_domains` are missing, configuration loading fails with an error

## Notes

- `coauthorcheck` only validates `Co-authored-by` trailers found in the final trailer block of the commit message.
- Lines elsewhere in the commit body are not treated as trailers.
- If a message has no `Co-authored-by` trailers, it is currently considered valid.
- When a trailer is invalid, `coauthorcheck` can also emit a suggested corrected trailer line. If multiple rules fail for the same trailer, the suggestion is merged into one canonical fix.
