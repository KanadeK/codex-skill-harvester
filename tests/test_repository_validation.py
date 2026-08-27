from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.validation import ValidationError, validate_repository


class RepositoryValidationTests(unittest.TestCase):
    def test_current_repository_has_safe_harvest_automation_and_community_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        required = (
            ".github/workflows/harvest.yml",
            ".github/dependabot.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/pull_request_template.md",
            "CODE_OF_CONDUCT.md",
            "SECURITY.md",
        )

        for name in required:
            self.assertTrue((root / name).is_file(), name)

        workflow = (root / ".github" / "workflows" / "harvest.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("pull-requests: write", workflow)
        self.assertIn("actions: write", workflow)
        self.assertIn("python -m skill_harvester scan --root .", workflow)
        self.assertIn("git add -- state/harvest-state.json candidates/inbox runs", workflow)
        self.assertIn('gh workflow run ci.yml --ref "$branch"', workflow)
        self.assertNotIn("skill_harvester apply", workflow)

        ci_workflow = (root / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_dispatch:", ci_workflow)

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
