from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.production import build_production_report, write_production_report
from skill_harvester.runtime_store import open_runtime_store


ROOT = Path(__file__).resolve().parents[1]


RUN_NAMES = [
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


def _copy_production_fixture(root: Path) -> None:
    (root / "state").mkdir(parents=True)
    (root / "runs").mkdir()
    (root / "config").mkdir()
    shutil.copy2(ROOT / "state" / "harvest.sqlite3", root / "state" / "harvest.sqlite3")
    shutil.copy2(
        ROOT / "config" / "campaign-policy.json",
        root / "config" / "campaign-policy.json",
    )
    for name in RUN_NAMES:
        shutil.copy2(ROOT / "runs" / name, root / "runs" / name)


def _report_arguments(root: Path) -> dict[str, object]:
    return {
        "generated_at": "2026-08-29T19:06:00Z",
        "campaign_report_path": root
        / "runs"
        / "2026-08-29T18-17-51.373491Z-campaign.json",
        "query_report_paths": [
            root / "runs" / "2026-08-29T18-12-00Z-queries.json",
            root / "runs" / "2026-08-29T18-59-00Z-queries.json",
            root / "runs" / "2026-08-29T19-02-00Z-queries.json",
        ],
        "semantic_report_paths": [
            root / "runs" / "2026-08-29T18-25-00Z-semantic.json",
            root / "runs" / "2026-08-29T18-54-00Z-semantic.json",
            root / "runs" / "2026-08-29T19-03-00Z-semantic.json",
        ],
        "supplemental_scan_paths": [
            root / "runs" / "2026-08-29T18-51-12.333437Z-scan.json",
            root / "runs" / "2026-08-29T18-56-37.216569Z-scan.json",
            root / "runs" / "2026-08-29T19-01-39.404341Z-scan.json",
        ],
        "query_no_op_report_path": root
        / "runs"
        / "2026-08-29T19-42-08.788092Z-query-export.json",
        "semantic_no_op_report_path": root
        / "runs"
        / "2026-08-29T19-53-21.086642Z-semantic-export.json",
        "stable_no_op_scan_path": root
        / "runs"
        / "2026-08-29T18-56-37.216569Z-scan.json",
    }


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
        self.assertEqual(report["slice"]["status"], "complete")
        self.assertEqual(report["status"], "active")
        self.assertFalse(report["objective"]["met"])
        self.assertEqual(report["objective"]["minimum_executable_endpoints"], 180)
        self.assertEqual(report["objective"]["minimum_actual_queries"], 1500)
        self.assertIn("next inventory/query batch", report["checkpoint"]["continuation"])

    def test_cycle_query_report_preserves_recoverable_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
            arguments = _report_arguments(root)
            for path in arguments["query_report_paths"]:
                query = json.loads(path.read_text(encoding="utf-8"))
                query["aggregation"] = "cycle"
                query["query_attempts"] = query["actual_queries"]
                query["actual_queries"] = query["completed_queries"]
                path.write_text(json.dumps(query), encoding="utf-8")

            report = build_production_report(root, **arguments)

        self.assertEqual(report["queries"]["actual_queries"], 21)
        self.assertEqual(report["queries"]["query_attempts"], 28)
        self.assertEqual(report["queries"]["failed_attempts"], 7)

    def test_objective_completion_is_required_for_campaign_completed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
            campaign_path = root / "runs" / RUN_NAMES[0]
            campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
            campaign["registered_endpoints"] = 179
            campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
            first_query_path = root / "runs" / RUN_NAMES[1]
            first_query = json.loads(first_query_path.read_text(encoding="utf-8"))
            first_query["completed_queries"] = 1490
            first_query_path.write_text(json.dumps(first_query), encoding="utf-8")

            report = build_production_report(root, **_report_arguments(root))

        self.assertEqual(report["discovery"]["executable_endpoints_after_selection"], 180)
        self.assertEqual(report["queries"]["actual_queries"], 1500)
        self.assertTrue(report["objective"]["met"])
        self.assertEqual(report["status"], "campaign_completed")
        self.assertEqual(report["objective"]["completion_basis"], "objective")

    def test_explicit_controller_end_completes_campaign_below_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
            policy_path = root / "config" / "campaign-policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["objective"]["controller_end"] = {
                "ended_at": "2026-08-30T12:30:00Z",
                "reason": "controller explicitly ended this campaign",
            }
            policy_path.write_text(json.dumps(policy), encoding="utf-8")

            report = build_production_report(root, **_report_arguments(root))

        self.assertFalse(report["objective"]["met"])
        self.assertEqual(report["status"], "campaign_completed")
        self.assertEqual(report["objective"]["completion_basis"], "controller")

    def test_stop_loss_is_a_resumable_campaign_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
            campaign_path = root / "runs" / RUN_NAMES[0]
            campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
            campaign["status"] = "checkpoint"
            campaign["stop_reasons"] = ["max_download_bytes reached"]
            campaign_path.write_text(json.dumps(campaign), encoding="utf-8")

            report = build_production_report(root, **_report_arguments(root))

        self.assertEqual(report["status"], "checkpoint")
        self.assertTrue(report["checkpoint"]["stop_loss"]["triggered"])
        self.assertEqual(
            report["checkpoint"]["stop_loss"]["reasons"],
            ["max_download_bytes reached"],
        )
        self.assertIn("persisted checkpoint", report["checkpoint"]["continuation"])

    def test_pending_discovery_hit_keeps_completed_queries_at_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
            with open_runtime_store(root) as store, store.connection:
                store.record_discovery_hits(
                    cycle_id="content-production-2026-08-29",
                    query={
                        "id": "daily-life-market-guide",
                        "source_group": "daily-life-market",
                        "topic_id": "daily-life.research.fresh-market",
                    },
                    observed_at="2026-08-30T20:00:00Z",
                    hits=[
                        {
                            "route": "github-code",
                            "url": "https://github.com/example/guides/blob/main/market.md",
                            "repository": "example/guides",
                            "path": "market.md",
                        }
                    ],
                )

            report = build_production_report(root, **_report_arguments(root))

        self.assertEqual(report["queries"]["discovery_review"]["pending"], 1)
        self.assertEqual(report["slice"]["pending_discovery_hits"], 1)
        self.assertEqual(report["status"], "checkpoint")
        self.assertIn("discovery-hit", report["checkpoint"]["continuation"])

    def test_historical_semantic_imports_do_not_duplicate_batch_or_hide_pending_l4(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            _copy_production_fixture(root)
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

            arguments = _report_arguments(root)
            arguments["semantic_report_paths"] = [
                historical_path,
                *arguments["semantic_report_paths"],
            ]
            report = build_production_report(root, **arguments)

            self.assertEqual(len(report["semantic"]["batch_ids"]), 3)
            self.assertEqual(report["semantic"]["normalized_candidates"], 3)
            self.assertEqual(report["l4"]["pending_candidates"], 1)
            self.assertEqual(report["status"], "checkpoint")


if __name__ == "__main__":
    unittest.main()
