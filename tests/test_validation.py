import unittest

from coauthorcheck.config import Config, RuleConfig
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

    def test_missing_name_and_email_format_errors_are_reported(self) -> None:
        result = validate_message(
            "commit3",
            "Subject\n\nCo-authored-by: <jane@example.com>\n",
        )

        codes = [issue.code for issue in result.issues]

        self.assertIn("invalid-format", codes)
        self.assertIn("missing-name", codes)

    def test_single_word_name_is_rejected(self) -> None:
        result = validate_message(
            "commit4",
            "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
        )

        self.assertIn("single-word-name", [issue.code for issue in result.issues])

    def test_missing_email_brackets_reports_missing_email(self) -> None:
        result = validate_message(
            "commit5",
            "Subject\n\nCo-authored-by: Jane Doe jane@example.com\n",
        )

        codes = [issue.code for issue in result.issues]
        self.assertIn("invalid-format", codes)
        self.assertIn("missing-email", codes)

    def test_single_word_name_rule_can_be_disabled(self) -> None:
        result = validate_message(
            "commit6",
            "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
            config=Config(rules=RuleConfig(single_word_name=False)),
        )

        self.assertNotIn("single-word-name", [issue.code for issue in result.issues])

    def test_github_handle_rule_can_be_disabled(self) -> None:
        result = validate_message(
            "commit7",
            "Subject\n\nCo-authored-by: @octocat <octocat@example.com>\n",
            config=Config(rules=RuleConfig(github_handle=False)),
        )

        self.assertNotIn("github-handle", [issue.code for issue in result.issues])


if __name__ == "__main__":
    unittest.main()
