from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.validation import ValidationError, validate_repository


class RepositoryValidationTests(unittest.TestCase):
    def test_current_repository_is_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]

        report = validate_repository(root)

        self.assertEqual(report["plugins"], 1)
        self.assertEqual(report["skills"], 1)
        self.assertEqual(report["internal_capabilities"], 1)
        self.assertEqual(report["secrets_found"], 0)

    def test_detects_generated_skill_drift(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            skill = (
                root
                / "plugins"
                / "github-release-evidence"
                / "skills"
                / "audit-github-release"
                / "SKILL.md"
            )
            skill.write_text(skill.read_text(encoding="utf-8") + "\nDrift.\n", encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "artifact hash"):
                validate_repository(root)


if __name__ == "__main__":
    unittest.main()
