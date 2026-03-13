import unittest

from coauthorcheck.validation import validate_message


class ValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
