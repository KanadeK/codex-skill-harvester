from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.scenario_bank import ScenarioBankError, load_scenario_bank


ROOT = Path(__file__).resolve().parents[1]


class ScenarioBankTests(unittest.TestCase):
    def test_current_daily_life_bank_has_three_resolved_twenty_plus_families(self) -> None:
        report = load_scenario_bank(ROOT)

        self.assertEqual(report["scenarios"], 63)
        self.assertEqual(
            report["by_family"],
            {
                "fresh-market-and-grocery-shopping": 21,
                "home-cooking-and-meal-preparation": 21,
                "laundry-and-clothing-care": 21,
            },
        )
        self.assertEqual(
            report["outcomes"], {"create": 9, "merge": 45, "not_promoted": 9}
        )
        self.assertEqual(report["pending"], 0)

    def test_pending_or_incomplete_scenario_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "catalog").mkdir()
            (root / "sources").mkdir()
            (root / "catalog" / "capabilities.json").write_text(
                json.dumps({"schema_version": 2, "internal": [], "external": []}),
                encoding="utf-8",
            )
            (root / "sources" / "registry.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "sources": [
                            {
                                "id": "fixture-source",
                                "adapter": "document",
                                "url": "https://example.test/guide",
                                "trust": "official",
                                "tier": "T1",
                                "authority": "fixture",
                                "license": {"status": "known", "identifier": "MIT"},
                            }
                        ],
                        "repository_sets": [],
                    }
                ),
                encoding="utf-8",
            )
            (root / "catalog" / "scenario-bank.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "families": [
                            {
                                "id": "fresh-market-and-grocery-shopping",
                                "plugin_id": "fresh-market-and-grocery-shopping",
                            }
                        ],
                        "scenarios": [
                            {
                                "id": "unfinished",
                                "family": "fresh-market-and-grocery-shopping",
                                "mode": "plan",
                                "user_request": {"zh": "帮我买菜"},
                                "critical_inputs": ["人数"],
                                "locality_conditions": ["本地市场"],
                                "equipment_conditions": ["储存空间"],
                                "observable_completion": ["清单完成"],
                                "recovery": ["缺货时替代"],
                                "safety_stop": ["过敏反应"],
                                "source_refs": ["fixture-source"],
                                "outcome": "pending",
                                "rationale": "This scenario has not received a final reviewed outcome yet.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ScenarioBankError, "terminal outcome"):
                load_scenario_bank(root, enforce_coverage=False)


if __name__ == "__main__":
    unittest.main()
