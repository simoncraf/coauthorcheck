import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from coauthorcheck.git_utils import GitError, interpret_git_error, read_commit_message, read_commit_range


def run_git(args: list[str], cwd: str) -> None:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.strip() or "git command failed during test setup")


class GitUtilsTests(unittest.TestCase):
    def test_interpret_not_a_repository_error(self) -> None:
        error = interpret_git_error(
            "fatal: not a git repository (or any of the parent directories): .git",
            ["show", "-s", "--format=%B", "HEAD"],
        )

        self.assertEqual(error.message, "current directory is not a git repository.")
        self.assertIsNotNone(error.hint)
        self.assertIn("commit message file path", error.hint)

    def test_interpret_safe_directory_error(self) -> None:
        error = interpret_git_error(
            "fatal: detected dubious ownership in repository at 'C:/repo'",
            ["show", "-s", "--format=%B", "HEAD"],
        )

        self.assertEqual(error.message, "git refused to read this repository because it is not marked as safe.")
        self.assertIsNotNone(error.hint)
        self.assertIn("safe.directory", error.hint)

    def test_interpret_invalid_range_error(self) -> None:
        error = interpret_git_error(
            "fatal: ambiguous argument 'HEAD~1000000..HEAD': unknown revision or path not in the working tree.",
            ["rev-list", "--reverse", "HEAD~1000000..HEAD"],
        )

        self.assertEqual(error.message, "unable to resolve revision range 'HEAD~1000000..HEAD'.")
        self.assertIsNotNone(error.hint)
        self.assertIn("main..HEAD", error.hint)

    def test_interpret_invalid_revision_error(self) -> None:
        error = interpret_git_error(
            "fatal: bad revision 'does-not-exist'",
            ["show", "-s", "--format=%B", "does-not-exist"],
        )

        self.assertEqual(error.message, "unable to resolve revision 'does-not-exist'.")
        self.assertEqual(error.hint, "Check that the commit, branch, or tag exists in the current repository.")

    def test_interpret_unknown_git_error_falls_back_to_raw_stderr(self) -> None:
        error = interpret_git_error(
            "fatal: some unexpected git failure",
            ["show", "-s", "--format=%B", "HEAD"],
        )

        self.assertEqual(error.message, "git failed to read commit messages.")
        self.assertEqual(error.hint, "fatal: some unexpected git failure")
        self.assertEqual(error.raw_error, "fatal: some unexpected git failure")

    def test_read_commit_message_reports_not_a_repository_with_real_git_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                Path(tmpdir).mkdir(exist_ok=True)
                # read_commit_message shells out without an explicit cwd, so switch for the duration.

                os.chdir(tmpdir)
                with self.assertRaises(GitError) as context:
                    read_commit_message("HEAD")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(context.exception.message, "current directory is not a git repository.")
        self.assertIsNotNone(context.exception.hint)
        self.assertIn("Git repository", context.exception.hint)

    def test_read_commit_range_reports_invalid_real_range_with_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_git(["init"], cwd=tmpdir)
            run_git(["config", "user.name", "Test User"], cwd=tmpdir)
            run_git(["config", "user.email", "test@example.com"], cwd=tmpdir)

            path = Path(tmpdir) / "README.md"
            path.write_text("hello\n", encoding="utf-8")
            run_git(["add", "README.md"], cwd=tmpdir)
            run_git(["commit", "-m", "Initial commit"], cwd=tmpdir)

            original_cwd = Path.cwd()
            try:
                os.chdir(tmpdir)
                with self.assertRaises(GitError) as context:
                    read_commit_range("HEAD~1000000..HEAD")
            finally:
                os.chdir(original_cwd)

        self.assertEqual(
            context.exception.message,
            "unable to resolve revision range 'HEAD~1000000..HEAD'.",
        )
        self.assertIsNotNone(context.exception.hint)
        self.assertIn("HEAD~1..HEAD", context.exception.hint)


if __name__ == "__main__":
    unittest.main()
