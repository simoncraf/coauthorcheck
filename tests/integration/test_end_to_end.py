from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.strip() or "git command failed during test setup")
    return completed


def run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else str(REPO_ROOT)
    )
    return subprocess.run(
        [sys.executable, "-m", "coauthorcheck", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def init_repo(path: Path) -> None:
    run_git(["init"], cwd=path)
    run_git(["config", "user.name", "Test User"], cwd=path)
    run_git(["config", "user.email", "test@example.com"], cwd=path)


def empty_commit(path: Path, message: str) -> None:
    run_git(["commit", "--allow-empty", "-m", message], cwd=path)


class EndToEndIntegrationTests(unittest.TestCase):
    def test_file_input_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            commit_message = repo / "COMMIT_MSG"
            commit_message.write_text(
                "Initial commit\n\nCo-authored-by: @simoncraf\n",
                encoding="utf-8",
            )

            completed = run_cli(["--file", str(commit_message)], cwd=repo)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("invalid-format", completed.stdout)
        self.assertIn("missing-email", completed.stdout)

    def test_commit_ref_end_to_end_passes_for_valid_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            empty_commit(
                repo,
                "Valid commit\n\nCo-authored-by: Jane Doe <jane@example.com>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 0)
        self.assertIn("OK HEAD", completed.stdout)
        self.assertIn("Summary: PASS", completed.stdout)

    def test_commit_ref_end_to_end_fails_for_invalid_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            empty_commit(
                repo,
                "Invalid commit\n\nCo-authored-by: @octocat <octocat>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("github-handle", completed.stdout)
        self.assertIn("malformed-email", completed.stdout)

    def test_commit_range_end_to_end_reports_only_invalid_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            empty_commit(repo, "Base commit")
            empty_commit(repo, "Valid commit\n\nCo-authored-by: Jane Doe <jane@example.com>")
            empty_commit(repo, "Invalid commit\n\nCo-authored-by: @octocat <octocat>")

            completed = run_cli(["HEAD~2..HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("OK", completed.stdout)
        self.assertIn("Issues", completed.stdout)
        self.assertIn("Summary: FAIL", completed.stdout)

    def test_warning_only_repo_policy_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            (repo / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "github_handle = 'warning'\n"
                "name_parts = false\n",
                encoding="utf-8",
            )
            empty_commit(
                repo,
                "Warn commit\n\nCo-authored-by: @octocat <octocat@example.com>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 0)
        self.assertIn("Warnings", completed.stdout)
        self.assertIn("Summary: PASS", completed.stdout)

    def test_minimum_name_parts_policy_fails_in_real_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            (repo / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "name_parts = 'error'\n"
                "[policy]\n"
                "minimum_name_parts = 3\n",
                encoding="utf-8",
            )
            empty_commit(
                repo,
                "Name policy commit\n\nCo-authored-by: Jane Doe <jane@example.com>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 1)
        self.assertIn("name-parts", completed.stdout)
        self.assertIn("Use at least 3 name", completed.stdout)
        self.assertIn("parts in the trailer.", completed.stdout)

    def test_minimum_name_parts_policy_can_relax_requirement_in_real_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            (repo / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "name_parts = 'error'\n"
                "[policy]\n"
                "minimum_name_parts = 1\n",
                encoding="utf-8",
            )
            empty_commit(
                repo,
                "Relaxed name policy\n\nCo-authored-by: Prince <prince@example.com>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 0)
        self.assertIn("Summary: PASS", completed.stdout)

    def test_email_domain_policy_fails_in_real_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            (repo / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "email_domain = 'error'\n"
                "[policy]\n"
                "allowed_email_domains = ['example.com']\n",
                encoding="utf-8",
            )
            empty_commit(
                repo,
                "Domain commit\n\nCo-authored-by: Jane Doe <jane@other.com>",
            )

            completed = run_cli(["--format", "json", "HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 1)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "fail")
        issue = payload["results"][0]["issues"][0]
        self.assertEqual(issue["code"], "email-domain")
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["suggestion"], "Co-authored-by: Jane Doe <jane@example.com>")

    def test_email_domain_rule_without_policy_is_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            init_repo(repo)
            (repo / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "email_domain = true\n",
                encoding="utf-8",
            )
            empty_commit(
                repo,
                "Config error commit\n\nCo-authored-by: Jane Doe <jane@example.com>",
            )

            completed = run_cli(["HEAD"], cwd=repo)

        self.assertEqual(completed.returncode, 2)
        self.assertIn("rules.email_domain", completed.stderr)
        self.assertIn("allowed_email_domains", completed.stderr)


if __name__ == "__main__":
    unittest.main()
