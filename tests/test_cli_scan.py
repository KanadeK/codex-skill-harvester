from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.cli import main
from skill_harvester.sources import FetchResponse

from _support import QueueFetcher, document_source, write_registry


class ScanCliTests(unittest.TestCase):
    def test_scan_command_reports_changed_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            output = io.StringIO()
            fetcher = QueueFetcher(
                FetchResponse(
                    200,
                    "https://example.test/official-doc.md",
                    {"etag": '"v1"'},
                    b"# Evidence",
                )
            )

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["scan", "--root", str(root)],
                    fetcher=fetcher,
                    now="2026-08-27T06:00:00Z",
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("status=changed", output.getvalue())
            self.assertIn("discoveries=1", output.getvalue())


if __name__ == "__main__":
    unittest.main()
