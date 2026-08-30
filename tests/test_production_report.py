from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.production import build_production_report, write_production_report
from skill_harvester.runtime_store import open_runtime_store


ROOT = Path(__file__).resolve().parents[1]


class ProductionReportTests(unittest.TestCase):
    def test_real_content_campaign_report_recomputes_every_funnel_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "production.json"
            report = write_production_report(
                ROOT,
                generated_at="2026-08-29T18:40:00Z",
                campaign_report_path=ROOT
                / "runs"
                / "2026-08-29T18-17-51.373491Z-campaign.json",
                query_report_paths=[
                    ROOT / "runs" / "2026-08-29T18-12-00Z-queries.json",
                    ROOT / "runs" / "2026-08-29T18-59-00Z-queries.json",
                    ROOT / "runs" / "2026-08-29T19-02-00Z-queries.json",
                ],
                semantic_report_paths=[
                    ROOT / "runs" / "2026-08-29T18-25-00Z-semantic.json",
                    ROOT / "runs" / "2026-08-29T18-54-00Z-semantic.json",
                    ROOT / "runs" / "2026-08-29T19-03-00Z-semantic.json",
                ],
                supplemental_scan_paths=[
                    ROOT / "runs" / "2026-08-29T18-51-12.333437Z-scan.json",
                    ROOT / "runs" / "2026-08-29T18-56-37.216569Z-scan.json",
                    ROOT / "runs" / "2026-08-29T19-01-39.404341Z-scan.json",
                ],
                query_no_op_report_path=ROOT
                / "runs"
                / "2026-08-29T19-42-08.788092Z-query-export.json",
                semantic_no_op_report_path=ROOT
                / "runs"
                / "2026-08-29T19-53-21.086642Z-semantic-export.json",
                stable_no_op_scan_path=ROOT
                / "runs"
                / "2026-08-29T18-56-37.216569Z-scan.json",
                output_path=output,
            )

        self.assertEqual(report["discovery"]["source_requests"], 28)
        self.assertEqual(report["discovery"]["inserted_observations"], 43)
        self.assertEqual(report["queries"]["actual_queries"], 21)
        self.assertEqual(report["queries"]["query_attempts"], 28)
        self.assertEqual(report["queries"]["failed_attempts"], 7)
        self.assertEqual(report["queries"]["pending_queries"], 0)
        self.assertEqual(
            report["queries"]["selected_source_ids"], ["pypa-sampleproject-readme"]
        )
        self.assertEqual(
            report["queries"]["cycle_ids"], ["content-production-2026-08-29"]
        )
        self.assertEqual(report["semantic"]["reviewed_observations"], 26)
        self.assertEqual(report["semantic"]["normalized_candidates"], 3)
        self.assertEqual(report["semantic"]["l3_recalls"], 9)
        self.assertEqual(report["l4"]["deep_reviews"], {"measured": True, "count": 3})
        self.assertEqual(report["l4"]["create"], 1)
        self.assertEqual(report["l4"]["update"], 1)
        self.assertEqual(report["l4"]["merge"], 1)
        self.assertEqual(report["l4"]["pending_candidates"], 0)
        self.assertEqual(report["cost"]["usage_credits"], {"measured": False})
        self.assertFalse(report["artifacts"]["release_published"])
        self.assertEqual(report["replay"]["query_rotation"], "no_op")

    def test_historical_semantic_imports_do_not_duplicate_batch_or_hide_pending_l4(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            (root / "state").mkdir(parents=True)
            (root / "runs").mkdir()
            (root / "state" / "harvest.sqlite3").write_bytes(
                (ROOT / "state" / "harvest.sqlite3").read_bytes()
            )
            names = [
                "2026-08-29T18-17-51.373491Z-campaign.json",
                "2026-08-29T18-12-00Z-queries.json",
                "2026-08-29T18-59-00Z-queries.json",
                "2026-08-29T19-02-00Z-queries.json",
                "2026-08-29T18-25-00Z-semantic.json",
                "2026-08-29T18-54-00Z-semantic.json",
                "2026-08-29T19-03-00Z-semantic.json",
                "2026-08-29T18-51-12.333437Z-scan.json",
                "2026-08-29T18-56-37.216569Z-scan.json",
                "2026-08-29T19-01-39.404341Z-scan.json",
                "2026-08-29T19-42-08.788092Z-query-export.json",
                "2026-08-29T19-53-21.086642Z-semantic-export.json",
            ]
            for name in names:
                (root / "runs" / name).write_bytes((ROOT / "runs" / name).read_bytes())
            first_semantic = json.loads(
                (root / "runs" / "2026-08-29T18-25-00Z-semantic.json").read_text(
                    encoding="utf-8"
                )
            )
            historical_path = root / "runs" / "2026-08-29T18-24-00Z-semantic.json"
            historical_path.write_text(
                json.dumps(
                    {
                        **first_semantic,
                        "reviewed_at": "2026-08-29T18:24:00Z",
                        "status": "pending",
                        "reviewed_observations": 0,
                        "pending_observations": 24,
                        "evidence_packs": 0,
                        "not_promoted": 0,
                        "normalized_candidates": 0,
                        "l2_matches": 0,
                        "l3_recalls": 0,
                    }
                ),
                encoding="utf-8",
            )
            with open_runtime_store(root) as store, store.connection:
                candidate = store.candidates_for_evidence_packs(
                    {
                        pack["id"]
                        for pack in store.evidence_packs_for_batch(
                            first_semantic["batch_id"]
                        )
                    }
                )[0]
                candidate["review_status"] = "pending"
                candidate.pop("decision_outcome", None)
                candidate.pop("decision_record", None)
                store.connection.execute(
                    "DELETE FROM decisions WHERE candidate_id = ?", (candidate["id"],)
                )
                store.connection.execute(
                    "UPDATE candidates SET review_status = 'pending', record_json = ? WHERE id = ?",
                    (json.dumps(candidate), candidate["id"]),
                )

            report = build_production_report(
                root,
                generated_at="2026-08-29T19:06:00Z",
                campaign_report_path=root
                / "runs"
                / "2026-08-29T18-17-51.373491Z-campaign.json",
                query_report_paths=[
                    root / "runs" / "2026-08-29T18-12-00Z-queries.json",
                    root / "runs" / "2026-08-29T18-59-00Z-queries.json",
                    root / "runs" / "2026-08-29T19-02-00Z-queries.json",
                ],
                semantic_report_paths=[
                    historical_path,
                    root / "runs" / "2026-08-29T18-25-00Z-semantic.json",
                    root / "runs" / "2026-08-29T18-54-00Z-semantic.json",
                    root / "runs" / "2026-08-29T19-03-00Z-semantic.json",
                ],
                supplemental_scan_paths=[
                    root / "runs" / "2026-08-29T18-51-12.333437Z-scan.json",
                    root / "runs" / "2026-08-29T18-56-37.216569Z-scan.json",
                    root / "runs" / "2026-08-29T19-01-39.404341Z-scan.json",
                ],
                query_no_op_report_path=root
                / "runs"
                / "2026-08-29T19-42-08.788092Z-query-export.json",
                semantic_no_op_report_path=root
                / "runs"
                / "2026-08-29T19-53-21.086642Z-semantic-export.json",
                stable_no_op_scan_path=root
                / "runs"
                / "2026-08-29T18-56-37.216569Z-scan.json",
            )

            self.assertEqual(len(report["semantic"]["batch_ids"]), 3)
            self.assertEqual(report["semantic"]["normalized_candidates"], 3)
            self.assertEqual(report["l4"]["pending_candidates"], 1)
            self.assertEqual(report["status"], "checkpoint")


if __name__ == "__main__":
    unittest.main()
