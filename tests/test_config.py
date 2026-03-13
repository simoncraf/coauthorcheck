import tempfile
import unittest
from pathlib import Path

from coauthorcheck.config import ConfigError, load_config


class ConfigTests(unittest.TestCase):
    def test_loads_pyproject_tool_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "pyproject.toml"
            path.write_text(
                "[tool.coauthorcheck.rules]\n"
                "single_word_name = false\n",
                encoding="utf-8",
            )

            config = load_config(config_path=path)

        self.assertFalse(config.rules.single_word_name)

    def test_loads_dedicated_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".coauthorcheck.toml"
            path.write_text(
                "[rules]\n"
                "github_handle = false\n",
                encoding="utf-8",
            )

            config = load_config(config_path=path)

        self.assertFalse(config.rules.github_handle)

    def test_dedicated_config_takes_precedence_over_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / ".coauthorcheck.toml").write_text(
                "[rules]\n"
                "single_word_name = false\n",
                encoding="utf-8",
            )
            (root / "pyproject.toml").write_text(
                "[tool.coauthorcheck.rules]\n"
                "single_word_name = true\n",
                encoding="utf-8",
            )

            config = load_config(start_dir=root)

        self.assertFalse(config.rules.single_word_name)

    def test_searches_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "a" / "b"
            nested.mkdir(parents=True)
            (root / "pyproject.toml").write_text(
                "[tool.coauthorcheck.rules]\n"
                "github_handle = false\n",
                encoding="utf-8",
            )

            config = load_config(start_dir=nested)

        self.assertFalse(config.rules.github_handle)

    def test_unknown_rule_raises_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".coauthorcheck.toml"
            path.write_text(
                "[rules]\n"
                "not_a_rule = true\n",
                encoding="utf-8",
            )

            with self.assertRaises(ConfigError) as context:
                load_config(config_path=path)

        self.assertIn("Unknown rule setting", str(context.exception))
