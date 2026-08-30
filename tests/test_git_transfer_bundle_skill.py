from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.evals import run_eval_file


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "git-offline-transfer"
    / "skills"
    / "create-git-transfer-bundle"
    / "scripts"
    / "git_transfer_bundle.py"
)


def git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def repository(root: Path) -> Path:
    repo = root / "source"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.name", "Fixture Author")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-m", "first")
    git(repo, "branch", "retained-branch")
    (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
    git(repo, "commit", "-am", "second")
    return repo


class GitTransferBundleSkillTests(unittest.TestCase):
    def run_script(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_create_verifies_and_clones_all_committed_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = repository(root)
            bundle = root / "transfer.bundle"

            created = self.run_script(
                "create", "--repo", str(source), "--output", str(bundle)
            )
            payload = json.loads(created.stdout)
            cloned = root / "receiver"
            subprocess.run(
                ["git", "clone", str(bundle), str(cloned)],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(payload["status"], "verified")
            self.assertTrue(bundle.is_file())
            self.assertIn("refs/heads/retained-branch", {item["ref"] for item in payload["advertised_refs"]})
            self.assertEqual(
                set(git(source, "rev-list", "--all").splitlines()),
                set(git(cloned, "rev-list", "--all").splitlines()),
            )

            verified = self.run_script(
                "verify", "--repo", str(source), "--bundle", str(bundle)
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(json.loads(verified.stdout)["mode"], "verify")

    def test_create_rejects_dirty_repository_and_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = repository(root)
            bundle = root / "transfer.bundle"
            (source / "untracked.txt").write_text("not committed\n", encoding="utf-8")

            dirty = self.run_script(
                "create", "--repo", str(source), "--output", str(bundle)
            )
            self.assertEqual(dirty.returncode, 2)
            self.assertIn("not clean", dirty.stderr)
            self.assertFalse(bundle.exists())

            (source / "untracked.txt").unlink()
            bundle.write_bytes(b"existing")
            existing = self.run_script(
                "create", "--repo", str(source), "--output", str(bundle)
            )
            self.assertEqual(existing.returncode, 2)
            self.assertIn("refusing to overwrite", existing.stderr)
            self.assertEqual(bundle.read_bytes(), b"existing")

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT,
                ROOT / "evals" / "create-git-transfer-bundle.json",
                Path(directory),
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["positive"], 3)
        self.assertEqual(report["negative"], 4)
        self.assertEqual(report["e2e_result"], "verified")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
