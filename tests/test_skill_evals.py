from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.evals import run_eval_file


class SkillEvalTests(unittest.TestCase):
    def test_reviewed_trigger_cases_and_e2e_snapshot_pass(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                root,
                root / "evals" / "audit-github-release.json",
                Path(directory),
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["positive"], 3)
        self.assertEqual(report["negative"], 4)
        self.assertEqual(report["e2e_result"], "complete")
        self.assertEqual(report["e2e_gates"], 7)


if __name__ == "__main__":
    unittest.main()
