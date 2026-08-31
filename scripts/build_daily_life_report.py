from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.daily_life_report import build_daily_life_report
from skill_harvester.io import atomic_write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Daily Life pilot report.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--query-no-op", type=Path, required=True)
    parser.add_argument("--semantic-no-op", type=Path, required=True)
    parser.add_argument("--stable-scan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    report = build_daily_life_report(
        root,
        generated_at=args.generated_at,
        query_no_op_path=(root / args.query_no_op).resolve(),
        semantic_no_op_path=(root / args.semantic_no_op).resolve(),
        stable_scan_path=(root / args.stable_scan).resolve(),
    )
    atomic_write_json((root / args.output).resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
