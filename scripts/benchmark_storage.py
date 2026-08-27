from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.scaling import (
    benchmark_json_lifecycle,
    evaluate_migration_triggers,
    inventory_repository,
    load_scale_policy,
    project_storage,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure the active Git-JSON lifecycle layout in a temporary directory."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--records", type=int)
    args = parser.parse_args()

    root = args.root.resolve()
    policy = load_scale_policy(root)
    records = args.records or policy["benchmark_fixture_records"]
    inventory = inventory_repository(root)
    report = {
        "schema_version": 1,
        "backend": policy["backend"],
        "inventory": inventory,
        "benchmark": benchmark_json_lifecycle(records),
        "projections": project_storage(inventory, policy),
        "migration_triggers": evaluate_migration_triggers(inventory, policy),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
