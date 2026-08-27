from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.release import build_release


class ReleaseBuildTests(unittest.TestCase):
    def test_release_archives_are_deterministic(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"

            first_files = build_release(root, first)
            second_files = build_release(root, second)

            self.assertEqual(
                [path.name for path in first_files],
                [
                    "codex-skill-harvester-v0.1.1.zip",
                    "github-release-evidence-v0.1.1.zip",
                    "SHA256SUMS.txt",
                ],
            )
            self.assertEqual([path.name for path in first_files], [path.name for path in second_files])
            for left, right in zip(first_files, second_files, strict=True):
                self.assertEqual(
                    hashlib.sha256(left.read_bytes()).digest(),
                    hashlib.sha256(right.read_bytes()).digest(),
                )


if __name__ == "__main__":
    unittest.main()
