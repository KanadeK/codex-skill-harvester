from __future__ import annotations

import json
import shutil
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
    / "javascript-package-delivery"
    / "skills"
    / "audit-npm-package-readiness"
    / "scripts"
    / "inspect_npm_package.py"
)


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )


def package(root: Path, *, scripts: dict[str, str] | None = None, secret: bool = False) -> None:
    metadata: dict[str, object] = {
        "name": "safe-fixture-package",
        "version": "1.2.3",
        "files": ["index.js", "README.md", "LICENSE"],
        "license": "MIT",
    }
    if scripts:
        metadata["scripts"] = scripts
    if secret:
        metadata["files"].append("secret.pem")
    (root / "package.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    (root / "index.js").write_text("export const value = 1;\n", encoding="utf-8")
    (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
    (root / "LICENSE").write_text("Fixture license\n", encoding="utf-8")
    if secret:
        (root / "secret.pem").write_text("not a real key\n", encoding="utf-8")
    git(root, "init")
    git(root, "config", "user.name", "Fixture Author")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "add", "package.json", "index.js", "README.md", "LICENSE")
    if secret:
        git(root, "add", "secret.pem")
    git(root, "commit", "-m", "fixture")


@unittest.skipUnless(shutil.which("npm"), "npm is required for the package E2E")
class NpmPackageSkillTests(unittest.TestCase):
    def run_script(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_clean_tracked_package_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package(root)
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["protections"]["ignore_scripts"])
        self.assertTrue(payload["protections"]["offline"])
        self.assertGreaterEqual(payload["payload"]["file_count"], 3)

    def test_declared_prepack_is_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "lifecycle-executed"
            package(
                root,
                scripts={
                    "prepack": "node -e \"require('fs').writeFileSync('lifecycle-executed','bad')\""
                },
            )
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertEqual(payload["status"], "unverified")
            self.assertIn("prepack", payload["declared_lifecycle_scripts"])
            self.assertFalse(marker.exists())

    def test_sensitive_payload_path_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package(root, secret=True)
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["status"], "not-ready")
        self.assertIn("secret.pem", payload["sensitive_paths"])

    def test_declared_types_entry_is_verified_in_dry_run_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package(root)
            metadata = json.loads((root / "package.json").read_text(encoding="utf-8"))
            metadata["types"] = "dist/index.d.ts"
            metadata["files"].append("dist/index.d.ts")
            (root / "package.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
            (root / "dist").mkdir()
            (root / "dist" / "index.d.ts").write_text(
                "export declare const value: number;\n", encoding="utf-8"
            )
            git(root, "add", "package.json", "dist/index.d.ts")
            git(root, "commit", "-m", "add declarations")
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["declarations"]["entry"], "dist/index.d.ts")
        self.assertTrue(payload["declarations"]["entry_in_payload"])

    def test_declared_types_entry_missing_from_payload_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package(root)
            metadata = json.loads((root / "package.json").read_text(encoding="utf-8"))
            metadata["types"] = "dist/index.d.ts"
            (root / "package.json").write_text(
                json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
            )
            (root / "dist").mkdir()
            (root / "dist" / "index.d.ts").write_text(
                "export declare const value: number;\n", encoding="utf-8"
            )
            git(root, "add", "package.json", "dist/index.d.ts")
            git(root, "commit", "-m", "declare missing payload types")
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["status"], "not-ready")
        self.assertFalse(payload["declarations"]["entry_in_payload"])
        self.assertIn("declared types entry is absent from the npm payload", payload["failures"])

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT, ROOT / "evals" / "audit-npm-package-readiness.json", Path(directory)
            )

        self.assertEqual(report["trigger_cases"], 8)
        self.assertEqual(report["e2e_result"], "ready")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
