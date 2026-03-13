import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from coauthorcheck.cli import app
from coauthorcheck.models import CommitMessage

runner = CliRunner()


class CliTests(unittest.TestCase):
    def test_no_input_is_rejected(self) -> None:
        result = runner.invoke(app, [])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("One input source is required.", result.output)

    def test_positional_file_input_success_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "COMMIT_MSG"
            path.write_text("Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n", encoding="utf-8")

            result = runner.invoke(app, [str(path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("OK", result.stdout)
        self.assertIn("Summary: PASS", result.stdout)

    def test_file_input_success_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "COMMIT_MSG"
            path.write_text("Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n", encoding="utf-8")

            result = runner.invoke(app, ["--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("OK", result.stdout)
        self.assertIn("Summary: PASS", result.stdout)

    def test_commit_range_failure_exit_code(self) -> None:
        commits = [
            CommitMessage(source="a1b2c3", message="Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n"),
            CommitMessage(source="d4e5f6", message="Subject\n\nCo-authored-by: @octocat <octocat>\n"),
        ]

        with patch("coauthorcheck.cli.read_commit_range", return_value=commits):
            result = runner.invoke(app, ["--range", "HEAD~1..HEAD"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("OK a1b2c3", result.stdout)
        self.assertIn("Issues d4e5f6", result.stdout)
        self.assertIn("malformed-email", result.stdout)
        self.assertIn("Summary: FAIL", result.stdout)

    def test_positional_range_input_is_detected(self) -> None:
        commits = [
            CommitMessage(source="a1b2c3", message="Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n"),
        ]

        with patch("coauthorcheck.cli.read_commit_range", return_value=commits):
            result = runner.invoke(app, ["HEAD~1..HEAD"])

        self.assertEqual(result.exit_code, 0)

    def test_existing_path_with_range_like_name_is_treated_as_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "HEAD..backup"
            path.write_text("Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n", encoding="utf-8")

            result = runner.invoke(app, [str(path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("OK", result.stdout)

    def test_positional_and_flag_together_are_rejected(self) -> None:
        result = runner.invoke(app, ["HEAD", "--commit", "HEAD"])
        self.assertEqual(result.exit_code, 2)
        self.assertIn("Provide either a positional input or an explicit flag", result.output)


if __name__ == "__main__":
    unittest.main()
