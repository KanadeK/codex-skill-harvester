from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.scaling import (
    ScalePolicyError,
    benchmark_json_lifecycle,
    benchmark_sqlite_runtime,
    evaluate_migration_triggers,
    inventory_repository,
    load_scale_policy,
    project_storage,
)


ROOT = Path(__file__).resolve().parents[1]


class ScalingTests(unittest.TestCase):
    def test_current_inventory_and_projection_are_data_backed(self) -> None:
        policy = load_scale_policy(ROOT)
        inventory = inventory_repository(ROOT)

        self.assertGreaterEqual(inventory["candidate_records"], 110)
        self.assertEqual(inventory["candidate_lifecycle_files"], 1)
        self.assertEqual(evaluate_migration_triggers(inventory, policy), [])

        projections = project_storage(inventory, policy)
        ten_thousand = next(
            item
            for item in projections["candidate_records"]
            if item["records"] == 10000
        )
        self.assertEqual(ten_thousand["lifecycle_files"], 1)
        self.assertGreater(ten_thousand["estimated_payload_bytes"], 20_000_000)

    def test_crossing_a_named_threshold_opens_migration_evaluation(self) -> None:
        policy = load_scale_policy(ROOT)
        inventory = inventory_repository(ROOT)
        crossed = deepcopy(inventory)
        crossed["candidate_records"] = 50000
        crossed["candidate_lifecycle_files"] = 150000
        crossed["harvest_state_bytes"] = 33554432
        crossed["seen_source_items"] = 100000

        triggers = evaluate_migration_triggers(
            crossed, policy, full_validation_seconds=60
        )

        self.assertEqual(
            triggers,
            [
                "candidate_lifecycle_files",
                "candidate_records",
                "full_validation_seconds",
                "harvest_state_bytes",
                "seen_source_items",
            ],
        )

    def test_temporary_benchmark_writes_and_reads_three_lifecycle_records(self) -> None:
        result = benchmark_json_lifecycle(25)

        self.assertEqual(result["records"], 25)
        self.assertEqual(result["files"], 75)
        self.assertEqual(result["parsed_files"], 75)
        self.assertGreater(result["bytes"], 0)
        self.assertGreaterEqual(result["write_seconds"], 0)
        self.assertGreaterEqual(result["read_seconds"], 0)

    def test_temporary_benchmark_rejects_zero_records(self) -> None:
        with self.assertRaisesRegex(ScalePolicyError, "positive integer"):
            benchmark_json_lifecycle(0)

    def test_temporary_sqlite_benchmark_writes_and_reads_one_runtime_store(self) -> None:
        result = benchmark_sqlite_runtime(25)

        self.assertEqual(result["records"], 25)
        self.assertEqual(result["parsed_records"], 25)
        self.assertGreater(result["bytes"], 0)
        self.assertGreaterEqual(result["write_seconds"], 0)
        self.assertGreaterEqual(result["read_seconds"], 0)

    def test_scale_policy_rejects_an_invalid_review_budget(self) -> None:
        policy = load_scale_policy(ROOT)
        invalid = deepcopy(policy)
        invalid["review_batch"]["default"] = 1001

        with self.assertRaisesRegex(ScalePolicyError, "review batch"):
            evaluate_migration_triggers({}, invalid)


if __name__ == "__main__":
    unittest.main()
