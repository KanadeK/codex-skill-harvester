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
    / "ansible-collection-quality"
    / "skills"
    / "validate-ansible-collection"
    / "scripts"
    / "plan_collection_tests.py"
)


class AnsibleCollectionSkillTests(unittest.TestCase):
    def run_script(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_plans_only_test_layers_present_in_valid_collection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            collection = (
                Path(directory) / "ansible_collections" / "acme" / "widgets"
            )
            (collection / "tests" / "unit").mkdir(parents=True)
            (collection / "tests" / "integration" / "targets").mkdir(parents=True)
            (collection / "galaxy.yml").write_text(
                "namespace: acme\nname: widgets\nversion: 1.2.3\n",
                encoding="utf-8",
            )

            completed = self.run_script(
                collection,
                "--ansible-core",
                "2.17",
                "--ansible-core",
                "2.18",
            )
            payload = json.loads(completed.stdout)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(payload["status"], "planned")
            self.assertFalse(payload["executed"])
            self.assertEqual(payload["ansible_core_matrix"], ["2.17", "2.18"])
            self.assertEqual(
                [layer["name"] for layer in payload["layers"]],
                ["sanity", "units", "integration"],
            )
            self.assertEqual(
                payload["layers"][0]["command"],
                ["ansible-test", "sanity", "--docker", "default", "-v"],
            )

    def test_rejects_wrong_layout_and_metadata_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrong_layout = root / "widgets"
            wrong_layout.mkdir()
            (wrong_layout / "galaxy.yml").write_text(
                "namespace: acme\nname: widgets\n", encoding="utf-8"
            )
            layout = self.run_script(wrong_layout)
            self.assertEqual(layout.returncode, 2)
            self.assertIn("ansible_collections", layout.stderr)

            collection = root / "ansible_collections" / "acme" / "widgets"
            collection.mkdir(parents=True)
            (collection / "galaxy.yml").write_text(
                "namespace: other\nname: widgets\n", encoding="utf-8"
            )
            identity = self.run_script(collection)
            self.assertEqual(identity.returncode, 2)
            self.assertIn("identity do not match", identity.stderr)

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT,
                ROOT / "evals" / "validate-ansible-collection.json",
                Path(directory),
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["positive"], 3)
        self.assertEqual(report["negative"], 4)
        self.assertEqual(report["e2e_result"], "planned")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
