from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.validation import ValidationError, validate_repository
from skill_harvester.queries import load_topic_bank
from skill_harvester.runtime_store import open_runtime_store


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
        self.assertIn("python -m skill_harvester campaign --root . --ramp", workflow)
        self.assertNotIn("python -m skill_harvester scan --root .", workflow)
        self.assertIn("git add -- state/harvest.sqlite3 runs", workflow)
        self.assertIn('gh workflow run ci.yml --ref "$branch"', workflow)
        self.assertNotIn("skill_harvester apply", workflow)

        ci_workflow = (root / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_dispatch:", ci_workflow)
        self.assertIn(
            "python scripts/benchmark_storage.py --root . --records 100",
            ci_workflow,
        )

    def test_current_repository_is_consistent(self) -> None:
        root = Path(__file__).resolve().parents[1]

        report = validate_repository(root)

        self.assertEqual(report["plugins"], 11)
        self.assertEqual(report["skills"], 17)
        self.assertEqual(report["internal_capabilities"], 17)
        self.assertEqual(report["taxonomy_version"], "1.2.0")
        self.assertEqual(report["scale_backend"], "sqlite-v4")
        self.assertEqual(report["evidence_packs"], 180)
        self.assertEqual(report["daily_life_scenarios"], 63)
        self.assertEqual(report["daily_life_scenario_pending"], 0)
        self.assertEqual(report["topic_queries"], len(load_topic_bank(root)))
        self.assertEqual(report["migration_triggers"], [])
        self.assertEqual(report["secrets_found"], 0)

    def test_existing_feed_noise_is_preserved_as_observations_not_queue_work(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with open_runtime_store(root) as store:
            pypi_observations = store.connection.execute(
                "SELECT COUNT(*) FROM observations WHERE source_id = ?",
                ("pypi-updates",),
            ).fetchone()[0]
            pypi_candidates = store.connection.execute(
                "SELECT COUNT(*) FROM candidates WHERE source_id = ?",
                ("pypi-updates",),
            ).fetchone()[0]
            release_observations = store.connection.execute(
                "SELECT COUNT(*) FROM observations WHERE source_id = ?",
                ("openai-codex-releases",),
            ).fetchone()[0]
            release_candidates = store.connection.execute(
                "SELECT COUNT(*) FROM candidates WHERE source_id = ?",
                ("openai-codex-releases",),
            ).fetchone()[0]
            pending_candidates = store.candidate_status_counts().get("pending", 0)

        self.assertGreaterEqual(pypi_observations, 200)
        self.assertEqual(pypi_candidates, 0)
        self.assertGreaterEqual(release_observations, 5)
        self.assertEqual(release_candidates, 11)
        self.assertGreater(release_observations, release_candidates)
        self.assertEqual(pending_candidates, 0)

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

    def test_detects_catalog_taxonomy_drift(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            path = root / "catalog" / "capabilities.json"
            catalog = json.loads(path.read_text(encoding="utf-8"))
            catalog["internal"][0]["classification"]["facets"]["domain"] = [
                "unregistered-domain"
            ]
            path.write_text(json.dumps(catalog), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "unregistered facet"):
                validate_repository(root)

    def test_detects_invalid_scale_policy(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            path = root / "config" / "scale-policy.json"
            policy = json.loads(path.read_text(encoding="utf-8"))
            policy["review_batch"]["default"] = 1001
            path.write_text(json.dumps(policy), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "review batch"):
                validate_repository(root)

    def test_rejects_a_second_legacy_runtime_authority(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            (root / "state" / "harvest-state.json").write_text(
                "{}\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValidationError, "legacy runtime authority"):
                validate_repository(root)

    def test_rejects_forged_campaign_stage_metrics(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            report = {
                "schema_version": 2,
                "report_type": "campaign",
                "campaign_id": "first-high-throughput",
                "run_id": "forged",
                "status": "checkpoint",
                "stop_reasons": ["test checkpoint"],
                "checkpoint": {
                    "completed_source_ids": [],
                    "pending_source_ids": [],
                    "last_successful_run": None,
                },
                "metrics": {
                    "source_requests": 0,
                    "source_successes": 0,
                    "source_success_rate": 0.0,
                    "failures": 0,
                    "raw_observations": 0,
                    "observations_inserted": 0,
                    "observation_duplicates": 0,
                    "normalized_candidates": 1,
                    "candidate_duplicates": 0,
                    "pending_queue": 0,
                    "l3_recalls": 0,
                    "downloaded_bytes": 0,
                    "runtime_store_bytes": 1,
                    "deep_reviews": {"measured": False},
                    "usage_credits": {"measured": False},
                },
                "runs": [],
            }
            path = root / "runs" / "forged-campaign.json"
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationError, "normalized_candidates does not match"
            ):
                validate_repository(root)

            report["metrics"]["normalized_candidates"] = 0
            report["metrics"]["deep_reviews"] = 0
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "deep_reviews"):
                validate_repository(root)

    def test_rejects_campaign_source_context_drift(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            path = next((root / "runs").glob("*-campaign.json"))
            report = json.loads(path.read_text(encoding="utf-8"))
            report["runs"][0]["sources"][0]["source_group"] = "wrong-group"
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "source context drift"):
                validate_repository(root)

    def test_rejects_forged_content_production_counts(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "*.pyc"),
            )
            path = next((root / "runs").glob("*-production.json"))
            report = json.loads(path.read_text(encoding="utf-8"))
            report["semantic"]["normalized_candidates"] += 1
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "authoritative inputs"):
                validate_repository(root)

            report["semantic"]["normalized_candidates"] -= 1
            report["l4"]["deep_reviews"]["count"] += 1
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "authoritative inputs"):
                validate_repository(root)

    def test_rejects_forged_cycle_query_attempt_count(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", "dist", ".harvester-cache", "__pycache__", "*.pyc"
                ),
            )
            path = next(
                path
                for path in (root / "runs").glob("*-queries.json")
                if json.loads(path.read_text(encoding="utf-8")).get("aggregation")
                == "cycle"
            )
            report = json.loads(path.read_text(encoding="utf-8"))
            report["query_attempts"] += 1
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationError, "query cycle stage counts disagree"
            ):
                validate_repository(root)

    def test_rejects_forged_discovery_hit_review_counts(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", "dist", ".harvester-cache", "__pycache__", "*.pyc"
                ),
            )
            path = next(
                path
                for path in (root / "runs").glob("*-queries.json")
                if json.loads(path.read_text(encoding="utf-8")).get("cycle_id")
                == "full-campaign-2026-08-30"
            )
            report = json.loads(path.read_text(encoding="utf-8"))
            report["discovery_review"]["duplicate"] -= 1
            report["discovery_review"]["not_selected"] += 1
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationError, "discovery review differs from SQLite"
            ):
                validate_repository(root)

    def test_rejects_forged_daily_life_pilot_report(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", "dist", ".harvester-cache", "__pycache__", "*.pyc"
                ),
            )
            path = root / "runs" / "2026-08-31-daily-life-pilot.json"
            report = json.loads(path.read_text(encoding="utf-8"))
            report["scenarios"]["total"] += 1
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(
                ValidationError, "Daily Life report does not match"
            ):
                validate_repository(root)

    def test_accepts_historical_partial_semantic_checkpoint_after_batch_completion(self) -> None:
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            shutil.copytree(
                source,
                root,
                ignore=shutil.ignore_patterns(
                    ".git", "dist", ".harvester-cache", "__pycache__", "*.pyc"
                ),
            )
            final_report_path = sorted((root / "runs").glob("*-semantic.json"))[0]
            final_report = json.loads(final_report_path.read_text(encoding="utf-8"))
            with open_runtime_store(root) as store:
                pending_at_start = len(
                    store.semantic_batch_items(final_report["batch_id"])
                )
                evidence_packs_at_start = store.connection.execute(
                    "SELECT COUNT(*) FROM evidence_packs"
                ).fetchone()[0]
            historical = {
                "schema_version": 1,
                "report_type": "semantic-review",
                "batch_id": final_report["batch_id"],
                "reviewed_at": "2026-08-29T18:24:00Z",
                "status": "pending",
                "reviewed_observations": 0,
                "pending_observations": pending_at_start,
                "evidence_packs": 0,
                "not_promoted": 0,
                "normalized_candidates": 0,
                "l2_matches": 0,
                "l3_recalls": 0,
                "deep_reviews": {"measured": False},
                "usage_credits": {"measured": False},
            }
            (root / "runs" / "2026-08-29T18-24-00Z-semantic.json").write_text(
                json.dumps(historical), encoding="utf-8"
            )

            report = validate_repository(root)

            self.assertEqual(report["evidence_packs"], evidence_packs_at_start)


if __name__ == "__main__":
    unittest.main()
