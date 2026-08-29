from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime as real_datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.cli import main
from skill_harvester.runtime_store import open_runtime_store
from skill_harvester.sources import FetchResponse

from _support import (
    QueueFetcher,
    document_source,
    write_registry,
    write_runtime_discovery,
    write_runtime_state,
)
from test_apply_decision import create_decision, write_json


ROOT = Path(__file__).resolve().parents[1]


def write_scale_policy(root: Path, *, default: int = 100, maximum: int = 1000) -> None:
    policy = json.loads(
        (ROOT / "config" / "scale-policy.json").read_text(encoding="utf-8")
    )
    policy["review_batch"] = {"default": default, "maximum": maximum}
    write_json(root / "config" / "scale-policy.json", policy)


class ScanCliTests(unittest.TestCase):
    def test_status_command_reports_durable_repository_counts_as_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("official-doc"), document_source("other-doc")])
            write_runtime_state(
                root,
                last_successful_run="2026-08-27T06:00:00Z",
                sources={"official-doc": {}, "other-doc": {}},
            )
            write_runtime_discovery(
                root,
                {
                    "id": "pending-one",
                    "source_id": "official-doc",
                    "title": "Pending one",
                    "trust": "official",
                    "license": {"status": "known"},
                    "canonical_url": "https://example.test/one",
                    "observed_at": "2026-08-27T06:00:00Z",
                    "review_status": "pending",
                },
            )
            write_runtime_discovery(
                root,
                {
                    "id": "applied-one",
                    "source_id": "other-doc",
                    "title": "Applied one",
                    "trust": "official",
                    "license": {"status": "known"},
                    "canonical_url": "https://example.test/two",
                    "observed_at": "2026-08-27T06:00:00Z",
                    "review_status": "applied",
                },
            )
            with open_runtime_store(root) as store:
                store.record_decision("applied-one", {"outcome": "discard"})
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [{"id": "plugin:skill"}], "external": []},
            )
            write_json(
                root / ".agents" / "plugins" / "marketplace.json",
                {"plugins": [{"name": "plugin"}]},
            )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(["status", "--root", str(root), "--json"])

            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["last_successful_run"], "2026-08-27T06:00:00Z")
            self.assertEqual(report["sources"]["registered"], 2)
            self.assertEqual(report["candidates"], {"total": 2, "pending": 1, "applied": 1})
            self.assertEqual(report["pending_by_source"], {"official-doc": 1})
            self.assertEqual(report["decision_outcomes"], {"not_promoted": 1})
            self.assertEqual(report["catalog"]["plugins"], 1)
            self.assertEqual(report["catalog"]["skills"], 1)

    def test_review_queue_filters_pending_candidates_by_registered_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("official-doc"), document_source("other-doc")])
            write_scale_policy(root)
            for candidate_id, source_id, status in (
                ("pending-one", "official-doc", "pending"),
                ("pending-two", "other-doc", "pending"),
                ("applied-one", "official-doc", "applied"),
            ):
                write_runtime_discovery(
                    root,
                    {
                        "id": candidate_id,
                        "source_id": source_id,
                        "title": candidate_id.replace("-", " "),
                        "trust": "official",
                        "license": {"status": "known"},
                        "canonical_url": f"https://example.test/{candidate_id}",
                        "observed_at": "2026-08-27T06:00:00Z",
                        "review_status": status,
                    },
                )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "review-queue",
                        "--root",
                        str(root),
                        "--source",
                        "official-doc",
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["pending"], 1)
            self.assertEqual(report["by_source"], {"official-doc": 1})
            self.assertEqual([item["id"] for item in report["items"]], ["pending-one"])

            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                exit_code = main(
                    ["review-queue", "--root", str(root), "--source", "missing-source"]
                )
            self.assertEqual(exit_code, 1)
            self.assertIn("unknown source id: missing-source", error.getvalue())

    def test_review_queue_is_priority_ordered_bounded_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            official = document_source("official-doc")
            representative = document_source("representative-doc")
            representative["trust"] = "representative"
            discovery = document_source("discovery-doc")
            discovery["trust"] = "discovery"
            write_registry(root, [discovery, representative, official])
            write_scale_policy(root)
            for candidate_id, source_id, trust in (
                ("discovery-one", "discovery-doc", "discovery"),
                ("representative-one", "representative-doc", "representative"),
                ("official-one", "official-doc", "official"),
            ):
                write_runtime_discovery(
                    root,
                    {
                        "id": candidate_id,
                        "source_id": source_id,
                        "title": candidate_id,
                        "trust": trust,
                        "license": {"status": "known"},
                        "canonical_url": f"https://example.test/{candidate_id}",
                        "observed_at": "2026-08-27T06:00:00Z",
                        "review_status": "pending",
                    },
                    queue=(
                        "official-gap"
                        if trust == "official"
                        else "novel-discovery"
                    ),
                )

            first_output = io.StringIO()
            with contextlib.redirect_stdout(first_output):
                first_exit = main(
                    ["review-queue", "--root", str(root), "--limit", "1", "--json"]
                )
            first = json.loads(first_output.getvalue())

            self.assertEqual(first_exit, 0)
            self.assertEqual(first["pending"], 3)
            self.assertEqual(first["returned"], 1)
            self.assertEqual(first["items"][0]["id"], "official-one")
            self.assertEqual(first["items"][0]["priority"], "high")
            self.assertEqual(first["next_cursor"], "official-one")

            second_output = io.StringIO()
            with contextlib.redirect_stdout(second_output):
                second_exit = main(
                    [
                        "review-queue",
                        "--root",
                        str(root),
                        "--limit",
                        "1",
                        "--after",
                        first["next_cursor"],
                        "--json",
                    ]
                )
            second = json.loads(second_output.getvalue())

            self.assertEqual(second_exit, 0)
            self.assertEqual(second["items"][0]["id"], "representative-one")
            self.assertNotEqual(
                first["items"][0]["id"], second["items"][0]["id"]
            )

    def test_review_queue_uses_repository_policy_default_page_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("official-doc")])
            write_scale_policy(root, default=2, maximum=3)
            for index in range(3):
                candidate_id = f"pending-{index}"
                write_runtime_discovery(
                    root,
                    {
                        "id": candidate_id,
                        "source_id": "official-doc",
                        "title": candidate_id,
                        "trust": "official",
                        "license": {"status": "known"},
                        "canonical_url": f"https://example.test/{candidate_id}",
                        "observed_at": "2026-08-27T06:00:00Z",
                        "review_status": "pending",
                    },
                )
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    ["review-queue", "--root", str(root), "--json"]
                )

            self.assertEqual(exit_code, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report["limit"], 2)
            self.assertEqual(report["returned"], 2)
            self.assertIsNotNone(report["next_cursor"])

    def test_review_queue_rejects_limit_above_repository_policy_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source("official-doc")])
            write_scale_policy(root, default=2, maximum=3)
            error = io.StringIO()
            output = io.StringIO()

            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                exit_code = main(
                    [
                        "review-queue",
                        "--root",
                        str(root),
                        "--limit",
                        "4",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("review limit must be between 1 and 3", error.getvalue())

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
