from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.sources import FetchResponse, SourceFetchError, run_scan

from _support import QueueFetcher, document_source, read_json, write_registry


class IncrementalScanTests(unittest.TestCase):
    def test_second_identical_run_is_noop_and_changed_third_run_is_incremental(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])

            first_fetcher = QueueFetcher(
                FetchResponse(
                    status=200,
                    final_url="https://example.test/official-doc.md",
                    headers={"etag": '"v1"', "last-modified": "Wed, 26 Aug 2026 12:00:00 GMT"},
                    body=b"# Release evidence\n\nVerify remote state.",
                )
            )
            first = run_scan(root, first_fetcher, now="2026-08-27T01:00:00Z")

            self.assertEqual(first["status"], "changed")
            self.assertEqual(first["discoveries"], 1)
            self.assertEqual(
                first["metrics"],
                {
                    "stage": "discovery",
                    "sources_selected": 1,
                    "sources_succeeded": 1,
                    "sources_failed": 0,
                    "source_success_rate": 1.0,
                    "discoveries_staged": 1,
                    "candidates_enqueued": 1,
                    "exact_record_duplicates": 0,
                },
            )
            first_candidates = sorted((root / "candidates" / "inbox").glob("*.json"))
            self.assertEqual(len(first_candidates), 1)

            second_fetcher = QueueFetcher(
                FetchResponse(
                    status=304,
                    final_url="https://example.test/official-doc.md",
                    headers={"etag": '"v1"'},
                    body=b"",
                )
            )
            second = run_scan(root, second_fetcher, now="2026-08-27T01:05:00Z")

            self.assertEqual(second["status"], "no_op")
            self.assertEqual(second["discoveries"], 0)
            self.assertEqual(second["metrics"]["candidates_enqueued"], 0)
            self.assertEqual(len(list((root / "candidates" / "inbox").glob("*.json"))), 1)
            self.assertEqual(second_fetcher.requests[0][1]["If-None-Match"], '"v1"')

            third_fetcher = QueueFetcher(
                FetchResponse(
                    status=200,
                    final_url="https://example.test/official-doc.md",
                    headers={"etag": '"v2"', "last-modified": "Thu, 27 Aug 2026 12:00:00 GMT"},
                    body=b"# Release evidence\n\nVerify remote state and contributors.",
                )
            )
            third = run_scan(root, third_fetcher, now="2026-08-27T01:10:00Z")

            self.assertEqual(third["status"], "changed")
            self.assertEqual(third["discoveries"], 1)
            self.assertEqual(len(list((root / "candidates" / "inbox").glob("*.json"))), 2)
            state = read_json(root / "state" / "harvest-state.json")
            self.assertEqual(state["sources"]["official-doc"]["etag"], '"v2"')
            self.assertEqual(state["last_successful_run"], "2026-08-27T01:10:00Z")

    def test_selected_sources_commit_state_only_when_all_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("one"), document_source("two")])
            initial_state = {
                "schema_version": 1,
                "last_successful_run": "2026-08-26T00:00:00Z",
                "sources": {},
            }
            state_path = root / "state" / "harvest-state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(json.dumps(initial_state, indent=2) + "\n", encoding="utf-8")
            before = state_path.read_bytes()
            fetcher = QueueFetcher(
                FetchResponse(
                    status=200,
                    final_url="https://example.test/one.md",
                    headers={"etag": '"one"'},
                    body=b"# One",
                ),
                SourceFetchError("source two failed"),
            )

            with self.assertRaisesRegex(SourceFetchError, "source two failed"):
                run_scan(root, fetcher, now="2026-08-27T02:00:00Z")

            self.assertEqual(state_path.read_bytes(), before)
            self.assertFalse((root / "candidates" / "inbox").exists())
            failed_reports = list((root / "runs").glob("*-failed.json"))
            self.assertEqual(len(failed_reports), 1)
            self.assertEqual(read_json(failed_reports[0])["status"], "failed")
            failed = read_json(failed_reports[0])
            self.assertEqual(failed["failed_source_id"], "two")
            self.assertEqual(failed["metrics"]["sources_selected"], 2)
            self.assertEqual(failed["metrics"]["sources_succeeded"], 1)
            self.assertEqual(failed["metrics"]["sources_failed"], 1)
            self.assertEqual(failed["metrics"]["source_success_rate"], 0.5)
            self.assertEqual(failed["metrics"]["candidates_enqueued"], 0)

    def test_existing_exact_discovery_record_is_not_reenqueued(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            response = FetchResponse(
                status=200,
                final_url="https://example.test/official-doc.md",
                headers={"etag": '"v1"'},
                body=b"# Evidence",
            )
            first = run_scan(
                root,
                QueueFetcher(response),
                now="2026-08-27T02:20:00Z",
            )
            (root / "state" / "harvest-state.json").unlink()

            recovered = run_scan(
                root,
                QueueFetcher(response),
                now="2026-08-27T02:25:00Z",
            )

            self.assertEqual(first["status"], "changed")
            self.assertEqual(recovered["status"], "no_op")
            self.assertEqual(recovered["discoveries"], 0)
            self.assertEqual(recovered["metrics"]["discoveries_staged"], 1)
            self.assertEqual(recovered["metrics"]["candidates_enqueued"], 0)
            self.assertEqual(recovered["metrics"]["exact_record_duplicates"], 1)
            self.assertEqual(
                len(list((root / "candidates" / "inbox").glob("*.json"))),
                1,
            )

    def test_programming_errors_are_not_reported_as_source_failures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            fetcher = QueueFetcher(RuntimeError("programming error"))

            with self.assertRaisesRegex(RuntimeError, "programming error"):
                run_scan(root, fetcher, now="2026-08-27T02:10:00Z")

            self.assertFalse((root / "runs").exists())


if __name__ == "__main__":
    unittest.main()
