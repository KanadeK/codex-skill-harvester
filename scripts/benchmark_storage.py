from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.scaling import (
    benchmark_json_lifecycle,
    benchmark_sqlite_runtime,
    evaluate_migration_triggers,
    inventory_repository,
    load_scale_policy,
    project_storage,
)
from skill_harvester.validation import validate_repository


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure active SQLite runtime storage and the legacy JSON lifecycle baseline."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--records", type=int)
    args = parser.parse_args()
    if args.records is not None and args.records <= 0:
        parser.error("--records must be a positive integer")

    root = args.root.resolve()
    policy = load_scale_policy(root)
    records = (
        args.records
        if args.records is not None
        else policy["benchmark_fixture_records"]
    )
    inventory = inventory_repository(root)
    validation_started = perf_counter()
    validate_repository(root)
    full_validation_seconds = perf_counter() - validation_started
    report = {
        "schema_version": 1,
        "backend": policy["backend"],
        "inventory": inventory,
        "full_validation_seconds": round(full_validation_seconds, 6),
        "benchmark": benchmark_sqlite_runtime(records),
        "legacy_json_baseline": benchmark_json_lifecycle(records),
        "projections": project_storage(inventory, policy),
        "migration_triggers": evaluate_migration_triggers(
            inventory,
            policy,
            full_validation_seconds=full_validation_seconds,
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
