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
    / "rust-build-performance"
    / "skills"
    / "measure-cargo-build-performance"
    / "scripts"
    / "measure_cargo_build.py"
)


def crate(root: Path, *, lock: bool = True) -> None:
    (root / "src").mkdir()
    (root / "Cargo.toml").write_text(
        '[package]\nname = "measure_fixture"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    (root / "src" / "lib.rs").write_text(
        "pub fn answer() -> u32 { 42 }\n", encoding="utf-8"
    )
    if lock:
        (root / "Cargo.lock").write_text(
            'version = 4\n\n[[package]]\nname = "measure_fixture"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )


@unittest.skipUnless(shutil.which("cargo"), "Cargo is required for the build E2E")
class CargoBuildPerformanceSkillTests(unittest.TestCase):
    def run_script(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_measures_cold_and_warm_builds_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crate(root)
            completed = self.run_script(root)
            payload = json.loads(completed.stdout)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["status"], "measured")
            self.assertEqual([run["phase"] for run in payload["runs"]], ["cold", "warm"])
            self.assertTrue(payload["protections"]["offline"])
            self.assertTrue(payload["protections"]["temporary_target_directory"])
            self.assertFalse((root / "target").exists())

    def test_missing_lockfile_fails_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crate(root, lock=False)
            completed = self.run_script(root)

        self.assertEqual(completed.returncode, 2)
        self.assertIn("Cargo.lock is required", completed.stderr)

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT, ROOT / "evals" / "measure-cargo-build-performance.json", Path(directory)
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["e2e_result"], "measured")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
