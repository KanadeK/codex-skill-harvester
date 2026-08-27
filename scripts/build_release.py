from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from skill_harvester.release import build_release


if __name__ == "__main__":
    for artifact in build_release(ROOT, ROOT / "dist"):
        print(artifact.relative_to(ROOT).as_posix())
