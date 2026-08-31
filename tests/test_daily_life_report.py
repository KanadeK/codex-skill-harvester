from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.daily_life_report import build_daily_life_report


ROOT = Path(__file__).resolve().parents[1]


class DailyLifeReportTests(unittest.TestCase):
    def test_current_pilot_rebuilds_every_stage_from_authority(self) -> None:
        report = build_daily_life_report(
            ROOT,
            generated_at="2026-08-31T05:30:00Z",
            query_no_op_path=ROOT
            / "runs"
            / "daily-life-pilot-2026-08-30-query-export.json",
            semantic_no_op_path=ROOT
            / "runs"
            / "2026-08-31T04-38-50.821414Z-semantic-export.json",
            stable_scan_path=ROOT
            / "runs"
            / "2026-08-31T04-39-08.958543Z-scan.json",
        )

        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["queries"]["completed"], 20)
        self.assertEqual(report["discovery_hits"]["unique_hits"], 18)
        self.assertEqual(report["discovery_hits"]["selected_endpoint"], 13)
        self.assertEqual(report["discovery_hits"]["not_selected"], 5)
        self.assertEqual(report["sources"]["selected"], 13)
        self.assertEqual(report["sources"]["scanned"], 13)
        self.assertEqual(
            report["sources"]["selection_failure_source_ids"],
            [
                "foodsafety-safe-temperatures",
                "usda-fsis-safe-temperatures",
                "usda-myplate-budget-planning",
                "usda-snaped-meal-planning",
                "usu-seasonal-meal-planning",
            ],
        )
        self.assertEqual(report["semantic"]["observations"], 13)
        self.assertEqual(report["semantic"]["evidence_packs"], 12)
        self.assertEqual(report["semantic"]["normalized_candidates"], 9)
        self.assertEqual(report["semantic"]["l3_recalls"], 156)
        self.assertEqual(report["l4"], {"create": 9, "merge": 0, "not_promoted": 0, "update": 0})
        self.assertEqual(report["scenarios"]["total"], 63)
        self.assertEqual(report["scenarios"]["pending"], 0)
        self.assertEqual(report["artifacts"], {"plugins": 3, "skills": 9, "release_published": False})
        self.assertEqual(report["evals"]["files"], 9)
        self.assertEqual(report["pending"], {"discovery_hits": 0, "semantic_observations": 0, "l4_candidates": 0})
        self.assertEqual(report["usage"], {"credits": {"measured": False}, "semantic_review_tokens": {"measured": False}})


if __name__ == "__main__":
    unittest.main()
