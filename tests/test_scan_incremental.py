from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.sources import FetchResponse, SourceFetchError, run_scan as _run_scan
from skill_harvester.runtime_store import open_runtime_store

from _support import (
    QueueFetcher,
    document_source,
    read_json,
    runtime_last_successful_run,
    runtime_source_state,
    scan_context,
    write_registry,
)


def run_scan(
    root: Path,
    fetcher: QueueFetcher,
    *,
    now: str,
    source_ids: set[str] | None = None,
) -> dict[str, object]:
    registry = json.loads((root / "sources" / "registry.json").read_text(encoding="utf-8"))
    selected = source_ids or {source["id"] for source in registry["sources"]}
    return _run_scan(
        root,
        fetcher,
        now=now,
        source_ids=selected,
        source_context=scan_context(*selected),
    )


class IncrementalScanTests(unittest.TestCase):
    def test_canonical_source_url_change_drops_old_conditionals_and_updates_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = document_source()
            write_registry(root, [source])
            run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, source["url"], {"etag": '"v1"'}, b"# Evidence")
                ),
                now="2026-08-27T00:50:00Z",
            )
            registry_path = root / "sources" / "registry.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            migrated_url = "https://example.test/canonical-official-doc.md"
            registry["sources"][0]["url"] = migrated_url
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            fetcher = QueueFetcher(
                FetchResponse(200, migrated_url, {"etag": '"v2"'}, b"# Evidence")
            )

            run_scan(root, fetcher, now="2026-08-27T00:55:00Z")

            self.assertNotIn("If-None-Match", fetcher.requests[0][1])
            self.assertEqual(runtime_source_state(root, "official-doc")["url"], migrated_url)

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
            self.assertEqual(first["observations"], 1)
            self.assertEqual(
                first["metrics"],
                {
                    "source_requests": 1,
                    "sources_succeeded": 1,
                    "failures": 0,
                    "source_success_rate": 1.0,
                    "raw_observations": 1,
                    "observations_staged": 1,
                    "observations_inserted": 1,
                    "observation_duplicates": 0,
                    "normalized_candidates": 0,
                    "candidate_duplicates": 0,
                    "l3_recalls": 0,
                    "downloaded_bytes": len(b"# Release evidence\n\nVerify remote state."),
                    "deep_reviews": {"measured": False},
                },
            )
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 1)
                self.assertEqual(store.candidate_count(), 0)

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
            self.assertEqual(second["observations"], 0)
            self.assertEqual(second["metrics"]["normalized_candidates"], 0)
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 1)
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
            self.assertEqual(third["observations"], 1)
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 2)
            self.assertEqual(runtime_source_state(root, "official-doc")["etag"], '"v2"')
            self.assertEqual(runtime_last_successful_run(root), "2026-08-27T01:10:00Z")

    def test_selected_sources_commit_state_only_when_all_succeed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("one"), document_source("two")])
            before = runtime_last_successful_run(root)
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

            self.assertEqual(runtime_last_successful_run(root), before)
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 0)
            failed_reports = list((root / "runs").glob("*-failed.json"))
            self.assertEqual(len(failed_reports), 1)
            self.assertEqual(read_json(failed_reports[0])["status"], "failed")
            failed = read_json(failed_reports[0])
            self.assertEqual(failed["failed_source_id"], "two")
            self.assertEqual(failed["metrics"]["source_requests"], 2)
            self.assertEqual(failed["metrics"]["sources_succeeded"], 1)
            self.assertEqual(failed["metrics"]["failures"], 1)
            self.assertEqual(failed["metrics"]["source_success_rate"], 0.5)
            self.assertEqual(failed["metrics"]["normalized_candidates"], 0)

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
            with open_runtime_store(root) as store:
                store.connection.execute("DELETE FROM source_states")
                store.connection.commit()

            recovered = run_scan(
                root,
                QueueFetcher(response),
                now="2026-08-27T02:25:00Z",
            )

            self.assertEqual(first["status"], "changed")
            self.assertEqual(recovered["status"], "no_op")
            self.assertEqual(recovered["observations"], 0)
            self.assertEqual(recovered["metrics"]["observations_staged"], 1)
            self.assertEqual(recovered["metrics"]["normalized_candidates"], 0)
            self.assertEqual(recovered["metrics"]["observation_duplicates"], 1)
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 1)

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
