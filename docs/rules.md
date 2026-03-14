# coauthorcheck rules

This page explains each validation rule supported by `coauthorcheck`.

All rule ids can be configured in either:

- `pyproject.toml` under `[tool.coauthorcheck.rules]`
- `.coauthorcheck.toml` under `[rules]`

Example:

```toml
[tool.coauthorcheck.rules]
single_word_name = false
github_handle = true
```

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

## single_word_name

Checks whether the name contains only one word.

When enabled, the rule requires at least two words in the co-author name.

Example:

```text
Co-authored-by: Prince <prince@example.com>
```

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

## Notes

- `coauthorcheck` only validates `Co-authored-by` trailers found in the final trailer block of the commit message.
- Lines elsewhere in the commit body are not treated as trailers.
- If a message has no `Co-authored-by` trailers, it is currently considered valid.
- When a trailer is invalid, `coauthorcheck` can also emit a suggested corrected trailer line. If multiple rules fail for the same trailer, the suggestion is merged into one canonical fix.
