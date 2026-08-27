from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.evals import run_eval_file


def main() -> int:
    reports = []
    with tempfile.TemporaryDirectory() as directory:
        temporary_directory = Path(directory)
        for eval_path in sorted((ROOT / "evals").glob("*.json")):
            reports.append(run_eval_file(ROOT, eval_path, temporary_directory))
    print(json.dumps(reports, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
