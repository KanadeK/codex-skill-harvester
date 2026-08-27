from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.validation import validate_repository


if __name__ == "__main__":
    print(json.dumps(validate_repository(ROOT), indent=2))
