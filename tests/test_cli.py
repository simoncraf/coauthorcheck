import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

from typer.testing import CliRunner

from coauthorcheck.cli import app
from coauthorcheck.git_utils import GitError
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

    def test_config_can_disable_single_word_name_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            message_path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            message_path.write_text(
                "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "single_word_name = false\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), str(message_path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Summary: PASS", result.stdout)

    def test_pyproject_config_is_auto_discovered_from_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "nested"
            nested.mkdir()
            message_path = nested / "COMMIT_MSG"
            message_path.write_text(
                "Subject\n\nCo-authored-by: Prince <prince@example.com>\n",
                encoding="utf-8",
            )
            (root / "pyproject.toml").write_text(
                "[tool.coauthorcheck.rules]\n"
                "single_word_name = false\n",
                encoding="utf-8",
            )

            original_cwd = Path.cwd()
            try:
                os.chdir(nested)
                result = runner.invoke(app, ["COMMIT_MSG"])
            finally:
                os.chdir(original_cwd)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Summary: PASS", result.stdout)

    def test_invalid_range_gets_actionable_hint(self) -> None:
        error = GitError(
            message="unable to resolve revision range 'HEAD~5..HEAD'.",
            hint=(
                "Try a smaller range like 'HEAD~1..HEAD', or validate only commits introduced by "
                "your branch with 'main..HEAD' or 'origin/main..HEAD'."
            ),
        )

        with patch("coauthorcheck.cli.read_commit_range", side_effect=error):
            result = runner.invoke(app, ["HEAD~5..HEAD"])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("unable to resolve revision range 'HEAD~5..HEAD'.", result.output)
        self.assertIn("main..HEAD", result.output)

    def test_not_a_repository_error_gets_file_hint(self) -> None:
        error = GitError(
            message="current directory is not a git repository.",
            hint="Run this command inside a Git repository, or pass a commit message file path instead.",
        )

        with patch("coauthorcheck.cli.read_commit_message", side_effect=error):
            result = runner.invoke(app, ["HEAD"])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("current directory is not a git repository.", result.output)
        self.assertIn("pass a commit message file", result.output)
        self.assertIn("path instead", result.output)


if __name__ == "__main__":
    unittest.main()
