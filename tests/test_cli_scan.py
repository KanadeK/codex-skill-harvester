from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from datetime import datetime as real_datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.cli import main
from skill_harvester.sources import FetchResponse

from _support import QueueFetcher, document_source, write_registry
from test_apply_decision import create_decision, write_json


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

    def test_apply_command_reports_reviewed_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root)
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["apply", "--root", str(root), "--decision", str(decision_path)]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("outcome=create", output.getvalue())
            self.assertIn("candidate=real-source-candidate", output.getvalue())

    @patch("skill_harvester.cli.datetime")
    def test_default_run_ids_do_not_collide_within_one_second(self, clock: object) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            clock.now.side_effect = [
                real_datetime(2026, 8, 27, 6, 0, 0, 100_000, tzinfo=timezone.utc),
                real_datetime(2026, 8, 27, 6, 0, 0, 200_000, tzinfo=timezone.utc),
            ]
            first = QueueFetcher(
                FetchResponse(200, "https://example.test/official-doc.md", {"etag": '"v1"'}, b"# Evidence")
            )
            second = QueueFetcher(
                FetchResponse(304, "https://example.test/official-doc.md", {"etag": '"v1"'}, b"")
            )

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["scan", "--root", str(root)], fetcher=first), 0)
                self.assertEqual(main(["scan", "--root", str(root)], fetcher=second), 0)

            self.assertEqual(len(list((root / "runs").glob("*-scan.json"))), 2)


if __name__ == "__main__":
    unittest.main()
