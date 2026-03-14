import unittest

from coauthorcheck.config import Config, RuleConfig, Severity
from coauthorcheck.validation import (
    EMAIL_PATTERN,
    GITHUB_HANDLE_PATTERN,
    NAME_EMAIL_PATTERN,
    validate_message,
)


class ValidationTests(unittest.TestCase):
    def test_name_email_pattern_matches_valid_name_and_email(self) -> None:
        match = NAME_EMAIL_PATTERN.match("Jane Doe <jane@example.com>")

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group("name"), "Jane Doe")
        self.assertEqual(match.group("email"), "jane@example.com")

    def test_name_email_pattern_rejects_missing_angle_brackets(self) -> None:
        self.assertIsNone(NAME_EMAIL_PATTERN.match("Jane Doe jane@example.com"))

    def test_email_pattern_accepts_standard_email(self) -> None:
        self.assertIsNotNone(EMAIL_PATTERN.match("jane.doe@example.com"))

    def test_email_pattern_rejects_malformed_email(self) -> None:
        self.assertIsNone(EMAIL_PATTERN.match("octocat"))
        self.assertIsNone(EMAIL_PATTERN.match("jane@@example.com"))
        self.assertIsNone(EMAIL_PATTERN.match("jane @example.com"))

    def test_github_handle_pattern_accepts_handle_like_names(self) -> None:
        self.assertIsNotNone(GITHUB_HANDLE_PATTERN.match("@octocat"))
        self.assertIsNotNone(GITHUB_HANDLE_PATTERN.match("@octo-cat"))

    def test_github_handle_pattern_rejects_regular_names(self) -> None:
        self.assertIsNone(GITHUB_HANDLE_PATTERN.match("Jane Doe"))
        self.assertIsNone(GITHUB_HANDLE_PATTERN.match("octocat"))

    def test_message_without_coauthor_trailers_is_valid(self) -> None:
        result = validate_message(
            "commit0",
            "Subject\n\nSigned-off-by: Jane Doe <jane@example.com>\n",
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, [])

    def test_valid_message_has_no_issues(self) -> None:
        result = validate_message(
            "commit1",
            "Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n",
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, [])

    def test_invalid_trailer_reports_expected_rules(self) -> None:
        result = validate_message(
            "commit2",
            "Subject\n\nco-authored-by: @octocat <octocat>\n",
        )

        codes = [issue.code for issue in result.issues]

        self.assertIn("incorrect-casing", codes)
        self.assertIn("github-handle", codes)
        self.assertIn("malformed-email", codes)
        message_map = {issue.code: issue.message for issue in result.issues}
        self.assertEqual(
            message_map["incorrect-casing"],
            "Use the exact trailer token 'Co-authored-by'.",
        )
        self.assertEqual(
            message_map["github-handle"],
            "Use a full name instead of a GitHub handle in the trailer.",
        )
        self.assertEqual(
            message_map["malformed-email"],
            "Use a valid email address in angle brackets.",
        )
        suggestions = {issue.suggestion for issue in result.issues}
        self.assertEqual(
            suggestions,
            {"Co-authored-by: Full Name <email@example.com>"},
        )

    def test_missing_name_and_email_format_errors_are_reported(self) -> None:
        result = validate_message(
            "commit3",
            "Subject\n\nCo-authored-by: <jane@example.com>\n",
        )

        codes = [issue.code for issue in result.issues]

        self.assertIn("invalid-format", codes)
        self.assertIn("missing-name", codes)
        message_map = {issue.code: issue.message for issue in result.issues}
        self.assertEqual(
            message_map["missing-name"],
            "Add the author name before the email address.",
        )

    def test_name_parts_rule_rejects_single_word_name_by_default(self) -> None:
        result = validate_message(
            "commit4",
            "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
        )

        self.assertIn("name-parts", [issue.code for issue in result.issues])
        message_map = {issue.code: issue.message for issue in result.issues}
        self.assertEqual(
            message_map["name-parts"],
            "Use at least a first and last name in the trailer.",
        )

    def test_missing_email_brackets_reports_missing_email(self) -> None:
        result = validate_message(
            "commit5",
            "Subject\n\nCo-authored-by: Jane Doe jane@example.com\n",
        )

        codes = [issue.code for issue in result.issues]
        self.assertIn("invalid-format", codes)
        self.assertIn("missing-email", codes)
        message_map = {issue.code: issue.message for issue in result.issues}
        self.assertEqual(
            message_map["missing-email"],
            "Add an email address in angle brackets, for example <email@example.com>.",
        )
        suggestions = {issue.suggestion for issue in result.issues}
        self.assertEqual(
            suggestions,
            {"Co-authored-by: Jane Doe <jane@example.com>"},
        )

    def test_name_parts_rule_can_be_disabled(self) -> None:
        result = validate_message(
            "commit6",
            "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
            config=Config(rules=RuleConfig(name_parts=False)),
        )

        self.assertNotIn("name-parts", [issue.code for issue in result.issues])

    def test_github_handle_rule_can_be_disabled(self) -> None:
        result = validate_message(
            "commit7",
            "Subject\n\nCo-authored-by: @octocat <octocat@example.com>\n",
            config=Config(rules=RuleConfig(github_handle=False)),
        )

        self.assertNotIn("github-handle", [issue.code for issue in result.issues])

    def test_minimum_name_parts_policy_can_require_more_than_two_parts(self) -> None:
        result = validate_message(
            "commit7b",
            "Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n",
            config=Config(
                rules=RuleConfig(name_parts="error"),
                minimum_name_parts=3,
            ),
        )

        self.assertEqual([issue.code for issue in result.issues], ["name-parts"])
        self.assertEqual(
            result.issues[0].message,
            "Use at least 3 name parts in the trailer.",
        )
        self.assertEqual(
            result.issues[0].suggestion,
            "Co-authored-by: Jane Doe Surname <jane@example.com>",
        )

    def test_minimum_name_parts_policy_can_relax_name_requirement(self) -> None:
        result = validate_message(
            "commit7c",
            "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
            config=Config(
                rules=RuleConfig(name_parts="error"),
                minimum_name_parts=1,
            ),
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, [])

    def test_warning_severity_does_not_invalidate_result(self) -> None:
        result = validate_message(
            "commit8",
            "Subject\n\nCo-authored-by: @octocat <octocat@example.com>\n",
            config=Config(
                rules=RuleConfig(
                    github_handle="warning",
                    name_parts=False,
                )
            ),
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 1)
        self.assertEqual(result.issues[0].severity, Severity.WARNING)

    def test_email_domain_policy_reports_issue_and_suggestion(self) -> None:
        result = validate_message(
            "commit9",
            "Subject\n\nCo-authored-by: Jane Doe <jane@other.com>\n",
            config=Config(
                rules=RuleConfig(email_domain="error"),
                allowed_email_domains=("example.com",),
            ),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual([issue.code for issue in result.issues], ["email-domain"])
        self.assertEqual(result.issues[0].message, "Use an email address from an allowed, non-blocked domain.")
        self.assertEqual(result.issues[0].suggestion, "Co-authored-by: Jane Doe <jane@example.com>")

    def test_blocked_email_domain_reports_issue_without_suggestion(self) -> None:
        result = validate_message(
            "commit10",
            "Subject\n\nCo-authored-by: Jane Doe <jane@users.noreply.github.com>\n",
            config=Config(
                rules=RuleConfig(email_domain="error"),
                blocked_email_domains=("users.noreply.github.com",),
            ),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual([issue.code for issue in result.issues], ["email-domain"])
        self.assertEqual(result.issues[0].message, "Use an email address from an allowed, non-blocked domain.")
        self.assertIsNone(result.issues[0].suggestion)

    def test_blocked_email_domain_can_suggest_single_allowed_domain(self) -> None:
        result = validate_message(
            "commit11",
            "Subject\n\nCo-authored-by: Jane Doe <jane@users.noreply.github.com>\n",
            config=Config(
                rules=RuleConfig(email_domain="error"),
                allowed_email_domains=("example.com",),
                blocked_email_domains=("users.noreply.github.com",),
            ),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.issues[0].suggestion, "Co-authored-by: Jane Doe <jane@example.com>")


if __name__ == "__main__":
    unittest.main()
