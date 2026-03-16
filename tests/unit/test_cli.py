import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os
import json
import subprocess
import sys

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

    def test_json_output_for_valid_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "COMMIT_MSG"
            path.write_text("Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n", encoding="utf-8")

            result = runner.invoke(app, ["--format", "json", "--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("tool_version", payload)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["summary"]["commit_count"], 1)
        self.assertEqual(payload["summary"]["invalid_commit_count"], 0)
        self.assertEqual(payload["results"][0]["source"], str(path))
        self.assertTrue(payload["results"][0]["is_valid"])
        self.assertEqual(payload["results"][0]["issues"], [])

    def test_warning_only_file_passes_with_warning_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: @octocat <octocat@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "github_handle = 'warning'\n"
                "name_parts = false\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("warning", result.stdout)
        self.assertIn("Summary: PASS", result.stdout)

    def test_json_output_includes_warning_severity_and_pass_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: @octocat <octocat@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "github_handle = 'warning'\n"
                "name_parts = false\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--format", "json", "--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("tool_version", payload)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["summary"]["invalid_commit_count"], 0)
        self.assertEqual(payload["summary"]["warning_commit_count"], 1)
        self.assertEqual(payload["summary"]["warning_count"], 1)
        self.assertEqual(payload["results"][0]["warning_count"], 1)
        self.assertEqual(payload["results"][0]["issues"][0]["severity"], "warning")

    def test_email_domain_policy_fails_with_error_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <jane@other.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "email_domain = 'error'\n"
                "[policy]\n"
                "allowed_email_domains = ['example.com']\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--format", "json", "--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("tool_version", payload)
        self.assertEqual(payload["status"], "fail")
        issue = payload["results"][0]["issues"][0]
        self.assertEqual(issue["code"], "email-domain")
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["suggestion"], "Co-authored-by: Jane Doe <jane@example.com>")

    def test_blocked_email_domain_policy_fails_without_suggestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <jane@users.noreply.github.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "email_domain = 'error'\n"
                "[policy]\n"
                "blocked_email_domains = ['users.noreply.github.com']\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--format", "json", "--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        issue = payload["results"][0]["issues"][0]
        self.assertEqual(issue["code"], "email-domain")
        self.assertIsNone(issue["suggestion"])

    def test_github_noreply_can_be_allowed_by_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <12345+jane@users.noreply.github.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "email_domain = 'error'\n"
                "[policy]\n"
                "allowed_email_domains = ['example.com']\n"
                "allow_github_noreply = true\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--format", "json", "--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["results"][0]["issues"], [])

    def test_ignore_bots_skips_bot_style_trailer_in_file_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[policy]\n"
                "ignore_bots = true\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Summary: PASS", result.stdout)

    def test_ignore_bots_skips_bot_authored_commit(self) -> None:
        commits = [
            CommitMessage(
                source="HEAD",
                message="Subject\n\nCo-authored-by: @octocat <octocat>\n",
                author_name="dependabot[bot]",
                author_email="49699333+dependabot[bot]@users.noreply.github.com",
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config_path = root / ".coauthorcheck.toml"
            config_path.write_text(
                "[policy]\n"
                "ignore_bots = true\n",
                encoding="utf-8",
            )

            with patch("coauthorcheck.cli.read_commit_message", return_value=commits[0]):
                result = runner.invoke(app, ["--config", str(config_path), "HEAD"])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Summary: PASS", result.stdout)

    def test_file_input_strips_git_comment_lines_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "COMMIT_MSG"
            path.write_text(
                "Initial commit\n\n"
                "Co-authored-by: @simoncraf\n"
                "# Please enter the commit message for your changes.\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--file", str(path)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("invalid-format", result.stdout)
        self.assertIn("missing-email", result.stdout)
        self.assertIn("Add an email", result.stdout)
        self.assertIn("address in angle", result.stdout)
        self.assertIn("brackets", result.stdout)
        self.assertIn("example", result.stdout)
        self.assertIn("Severity", result.stdout)
        self.assertIn("Suggestion", result.stdout)
        self.assertIn("Co-authored-by:", result.stdout)
        self.assertIn("@simoncraf", result.stdout)
        self.assertIn("<email@example.com>", result.stdout)
        self.assertEqual(result.stdout.count("@simoncraf"), 1)

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

    def test_json_output_for_invalid_range(self) -> None:
        commits = [
            CommitMessage(source="a1b2c3", message="Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n"),
            CommitMessage(source="d4e5f6", message="Subject\n\nCo-authored-by: @octocat <octocat>\n"),
        ]

        with patch("coauthorcheck.cli.read_commit_range", return_value=commits):
            result = runner.invoke(app, ["--format", "json", "--range", "HEAD~1..HEAD"])

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("tool_version", payload)
        self.assertEqual(payload["status"], "fail")
        self.assertEqual(payload["summary"]["commit_count"], 2)
        self.assertEqual(payload["summary"]["invalid_commit_count"], 1)
        self.assertEqual(payload["summary"]["issue_count"], 2)
        self.assertEqual(payload["results"][0]["issue_count"], 0)
        self.assertEqual(payload["results"][1]["source"], "d4e5f6")
        self.assertFalse(payload["results"][1]["is_valid"])
        issue_map = {issue["code"]: issue for issue in payload["results"][1]["issues"]}
        self.assertIn("malformed-email", issue_map)
        self.assertIn("github-handle", issue_map)
        self.assertEqual(
            issue_map["github-handle"]["suggestion"],
            "Co-authored-by: Full Name <email@example.com>",
        )
        self.assertEqual(
            issue_map["malformed-email"]["suggestion"],
            "Co-authored-by: Full Name <email@example.com>",
        )

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

    def test_config_can_disable_name_parts_rule(self) -> None:
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
                "name_parts = false\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), str(message_path)])

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Summary: PASS", result.stdout)

    def test_config_can_require_three_name_parts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            message_path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            message_path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "name_parts = 'error'\n"
                "[policy]\n"
                "minimum_name_parts = 3\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), str(message_path)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("name-parts", result.stdout)
        self.assertIn("Use at least 3 name", result.stdout)
        self.assertIn("parts in the trailer.", result.stdout)
        self.assertIn("Co-authored-by: Jane", result.stdout)
        self.assertIn("Doe Surname", result.stdout)

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
                "name_parts = false\n",
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

    def test_json_error_output_for_git_failure(self) -> None:
        error = GitError(
            message="current directory is not a git repository.",
            hint="Run this command inside a Git repository, or pass a commit message file path instead.",
        )

        with patch("coauthorcheck.cli.read_commit_message", side_effect=error):
            result = runner.invoke(app, ["--format", "json", "HEAD"])

        self.assertEqual(result.exit_code, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("tool_version", payload)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["message"], "current directory is not a git repository.")
        self.assertIn("commit message file path", payload["error"]["hint"])

    def test_config_error_when_email_domain_rule_has_no_allowed_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[rules]\n"
                "email_domain = true\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("'rules.email_domain'", result.output)
        self.assertIn("allowed_email_domains", result.output)
        self.assertIn("blocked_email_domains", result.output)
        self.assertIn("allow_github_noreply", result.output)

    def test_config_error_when_minimum_name_parts_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "COMMIT_MSG"
            config_path = root / ".coauthorcheck.toml"
            path.write_text(
                "Subject\n\nCo-authored-by: Jane Doe <jane@example.com>\n",
                encoding="utf-8",
            )
            config_path.write_text(
                "[policy]\n"
                "minimum_name_parts = 0\n",
                encoding="utf-8",
            )

            result = runner.invoke(app, ["--config", str(config_path), "--file", str(path)])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("policy.minimum_name_parts", result.output)
        self.assertIn("greater than or equal to 1", result.output)

    def test_module_exit_code_is_nonzero_for_validation_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "COMMIT_MSG"
            path.write_text("Initial commit\n\nCo-authored-by: @simoncraf\n", encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, "-m", "coauthorcheck", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("invalid-format", completed.stdout)


if __name__ == "__main__":
    unittest.main()
