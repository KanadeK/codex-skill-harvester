from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.discovery_review import (
    DiscoveryReviewError,
    export_discovery_review_batch,
    import_discovery_reviews,
    reopen_failed_selection,
)
from skill_harvester.io import atomic_write_json
from skill_harvester.queries import QueryBatchError, export_query_batch, import_query_results
from skill_harvester.runtime_store import open_runtime_store

from _support import document_source, write_registry


def prepare_query(
    root: Path,
    *,
    query_id: str = "market-guide",
    route: str = "github-code",
) -> dict[str, object]:
    write_registry(root, [document_source("existing-official-doc")])
    (root / "config").mkdir(exist_ok=True)
    atomic_write_json(
        root / "config" / "topic-bank.json",
        {
            "schema_version": 2,
            "topics": [
                {
                    "id": "daily-life.research.fresh-market",
                    "domain": "daily-life",
                    "intent": "research",
                    "source_group": "daily-life-market",
                    "queries": [
                        {
                            "id": query_id,
                            "route": route,
                            "text": (
                                "repo:example/official-guides grocery planning"
                                if route == "github-code"
                                else "official grocery planning food safety guidance"
                            ),
                            "tier_constraint": ["T0", "T1", "T2"],
                        }
                    ],
                }
            ],
            "operations": [],
            "query_matrices": [],
        },
    )
    export_path = root / ".harvester-cache" / "query.json"
    return export_query_batch(
        root,
        now="2026-08-30T20:00:00Z",
        cycle_id="daily-life-pilot",
        limit=10,
        output_path=export_path,
    )


def import_hits(
    root: Path,
    batch_id: str,
    hits: list[dict[str, str]],
    *,
    selected_endpoints: list[dict[str, object]] | None = None,
    executed_at: str = "2026-08-30T20:01:00Z",
) -> dict[str, object]:
    path = root / ".harvester-cache" / "query-results.json"
    atomic_write_json(
        path,
        {
            "schema_version": 1,
            "batch_id": batch_id,
            "executed_by": "codex-agent-reach",
            "executed_at": executed_at,
            "results": [
                {
                    "query_id": "market-guide",
                    "status": "completed",
                    "cursor": None,
                    "result_count": len(hits),
                    "discovery_hits": hits,
                    "selected_endpoints": selected_endpoints or [],
                }
            ],
        },
    )
    return import_query_results(root, batch_id=batch_id, results_path=path)


class DiscoveryReviewTests(unittest.TestCase):
    def test_failed_unscanned_selection_reopens_without_erasing_review_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root, route="web")
            hit = {
                "route": "web",
                "url": "https://www.example.gov/blocked-guide",
                "title": "Blocked official guide",
                "source_name": "Example Government",
            }
            import_hits(root, str(batch["batch_id"]), [hit])
            export_path = root / ".harvester-cache" / "discovery.json"
            export_discovery_review_batch(
                root,
                now="2026-08-30T20:02:00Z",
                limit=10,
                after=None,
                output_path=export_path,
            )
            hit_id = json.loads(export_path.read_text(encoding="utf-8"))["hits"][0]["id"]
            review_path = root / ".harvester-cache" / "review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-30T20:03:00Z",
                    "items": [
                        {
                            "hit_id": hit_id,
                            "outcome": "selected_endpoint",
                            "assessed_trust": "official",
                            "license_assessment": {
                                "status": "facts-only",
                                "identifier": "government-public-information",
                            },
                            "rationale": (
                                "The reviewed government page appears authoritative and useful, "
                                "so it is selected subject to a reproducible source scan."
                            ),
                            "selected_endpoint": {
                                "source_id": "blocked-official-guide",
                                "url": hit["url"],
                                "adapter": "document",
                                "tier": "T1",
                                "trust": "official",
                                "authority": "government-consumer-guidance",
                                "license": {
                                    "status": "facts-only",
                                    "identifier": "government-public-information",
                                },
                                "cursor": "reviewed-2026-08-30",
                            },
                        }
                    ],
                },
            )
            import_discovery_reviews(root, review_path=review_path)

            report = reopen_failed_selection(
                root,
                hit_id=hit_id,
                reopened_at="2026-08-30T20:04:00Z",
                reason="The selected endpoint returned HTTP 403 before any source state was committed.",
            )
            registry = json.loads(
                (root / "sources" / "registry.json").read_text(encoding="utf-8")
            )
            with open_runtime_store(root) as store:
                record = store.discovery_hit(hit_id)

        self.assertEqual(report["status"], "reopened")
        self.assertEqual(record["status"], "pending")
        self.assertIsNone(record["review"])
        self.assertEqual(len(record["review_history"]), 1)
        self.assertNotIn(
            "blocked-official-guide", [source["id"] for source in registry["sources"]]
        )

    def test_agent_reach_web_hit_uses_the_same_review_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root, route="web")
            hit = {
                "route": "web",
                "url": "https://www.example.gov/food/grocery-planning",
                "title": "Plan groceries safely",
                "source_name": "Example Food Safety Authority",
            }
            import_hits(root, str(batch["batch_id"]), [hit])
            export_path = root / ".harvester-cache" / "web-discovery.json"
            export_discovery_review_batch(
                root,
                now="2026-08-30T20:02:00Z",
                limit=10,
                after=None,
                output_path=export_path,
            )
            hit_id = json.loads(export_path.read_text(encoding="utf-8"))["hits"][0]["id"]
            review_path = root / ".harvester-cache" / "web-review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-30T20:03:00Z",
                    "items": [
                        {
                            "hit_id": hit_id,
                            "outcome": "selected_endpoint",
                            "assessed_trust": "official",
                            "license_assessment": {
                                "status": "facts-only",
                                "identifier": "government-public-information",
                            },
                            "rationale": (
                                "The reviewed government page provides operational grocery "
                                "planning and food-safety decisions with clear public provenance."
                            ),
                            "selected_endpoint": {
                                "source_id": "government-grocery-planning",
                                "url": hit["url"],
                                "adapter": "document",
                                "tier": "T1",
                                "trust": "official",
                                "authority": "government-food-safety-guidance",
                                "license": {
                                    "status": "facts-only",
                                    "identifier": "government-public-information",
                                },
                                "cursor": "reviewed-2026-08-30",
                            },
                        }
                    ],
                },
            )

            report = import_discovery_reviews(root, review_path=review_path)

        self.assertEqual(report["selected_endpoint"], 1)
        self.assertEqual(report["pending"], 0)

    def test_duplicate_and_not_selected_reviews_are_terminal_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root)
            hits = [
                {
                    "route": "github-code",
                    "url": "https://github.com/example/official-guides/blob/main/duplicate.md",
                    "repository": "example/official-guides",
                    "path": "duplicate.md",
                },
                {
                    "route": "github-code",
                    "url": "https://github.com/example/unknown-guides/blob/main/post.md",
                    "repository": "example/unknown-guides",
                    "path": "post.md",
                },
            ]
            import_hits(root, str(batch["batch_id"]), hits)
            export_path = root / ".harvester-cache" / "discovery.json"
            export_discovery_review_batch(
                root,
                now="2026-08-30T20:02:00Z",
                limit=10,
                after=None,
                output_path=export_path,
            )
            records = json.loads(export_path.read_text(encoding="utf-8"))["hits"]
            by_path = {record["hit"]["path"]: record for record in records}
            review_path = root / ".harvester-cache" / "review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-30T20:03:00Z",
                    "items": [
                        {
                            "hit_id": by_path["duplicate.md"]["id"],
                            "outcome": "duplicate",
                            "assessed_trust": "official",
                            "license_assessment": {
                                "status": "known",
                                "identifier": "CC0-1.0",
                            },
                            "duplicate_source_id": "existing-official-doc",
                            "rationale": (
                                "The hit repeats the same official workflow and source identity "
                                "already represented by the registered endpoint."
                            ),
                            "reactivation_conditions": [
                                "Reconsider if the source adds a materially different user workflow."
                            ],
                        },
                        {
                            "hit_id": by_path["post.md"]["id"],
                            "outcome": "not_selected",
                            "assessed_trust": "discovery",
                            "license_assessment": {
                                "status": "unknown",
                                "identifier": None,
                            },
                            "rationale": (
                                "The repository metadata does not establish official authority, "
                                "a reusable workflow, or permission to retain operational content."
                            ),
                            "reactivation_conditions": [
                                "Reconsider when a T0/T1 source corroborates the workflow and license."
                            ],
                        },
                    ],
                },
            )

            first = import_discovery_reviews(root, review_path=review_path)
            repeated = import_discovery_reviews(root, review_path=review_path)
            with open_runtime_store(root) as store:
                metrics = store.discovery_review_metrics()

        self.assertEqual(first["duplicate"], 1)
        self.assertEqual(first["not_selected"], 1)
        self.assertEqual(first["pending"], 0)
        self.assertEqual(repeated["status"], "no_op")
        self.assertEqual(repeated["no_op"], 2)
        self.assertEqual(metrics["duplicate"], 1)
        self.assertEqual(metrics["not_selected"], 1)

    def test_query_hits_become_pending_and_direct_selection_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root)
            hit = {
                "route": "github-code",
                "url": "https://github.com/example/official-guides/blob/main/market.md",
                "repository": "example/official-guides",
                "path": "market.md",
            }
            with self.assertRaisesRegex(QueryBatchError, "discovery review"):
                import_hits(
                    root,
                    str(batch["batch_id"]),
                    [hit],
                    selected_endpoints=[
                        {
                            "source_id": "bypass-source",
                            "url": "https://example.test/guide",
                            "adapter": "document",
                            "tier": "T1",
                            "trust": "official",
                            "authority": "official-operational-guide",
                            "license": {"status": "known", "identifier": "CC0-1.0"},
                        }
                    ],
                )

            report = import_hits(root, str(batch["batch_id"]), [hit])
            summary = json.loads(
                (root / "runs" / "daily-life-pilot-queries.json").read_text(
                    encoding="utf-8"
                )
            )
            with open_runtime_store(root) as store:
                pending = store.discovery_review_page(limit=10, after=None)

        self.assertEqual(report["discovery_hits"], 1)
        self.assertEqual(summary["discovery_review"]["pending"], 1)
        self.assertEqual(summary["discovery_review"]["selected_endpoint"], 0)
        self.assertEqual(summary["discovery_review"]["conversion_rate"], 0.0)
        self.assertEqual(len(pending["records"]), 1)
        self.assertEqual(pending["records"][0]["status"], "pending")

    def test_partial_review_selects_known_license_source_and_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root)
            first_hit = {
                "route": "github-code",
                "url": "https://github.com/example/official-guides/blob/main/market.md",
                "repository": "example/official-guides",
                "path": "market.md",
            }
            second_hit = {
                "route": "github-code",
                "url": "https://github.com/example/official-guides/blob/main/laundry.md",
                "repository": "example/official-guides",
                "path": "laundry.md",
            }
            import_hits(root, str(batch["batch_id"]), [first_hit, second_hit])
            export_path = root / ".harvester-cache" / "discovery.json"
            exported = export_discovery_review_batch(
                root,
                now="2026-08-30T20:02:00Z",
                limit=10,
                after=None,
                output_path=export_path,
            )
            hits = json.loads(export_path.read_text(encoding="utf-8"))["hits"]
            review_path = root / ".harvester-cache" / "review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-30T20:03:00Z",
                    "items": [
                        {
                            "hit_id": hits[0]["id"],
                            "outcome": "selected_endpoint",
                            "assessed_trust": "official",
                            "license_assessment": {
                                "status": "known",
                                "identifier": "CC0-1.0",
                            },
                            "rationale": (
                                "The reviewed page is an official operational guide with a "
                                "distinct grocery-planning workflow and traceable revision."
                            ),
                            "selected_endpoint": {
                                "source_id": "official-market-guide",
                                "url": "https://raw.githubusercontent.com/example/official-guides/0123456789012345678901234567890123456789/market.md",
                                "adapter": "document",
                                "tier": "T1",
                                "trust": "official",
                                "authority": "official-operational-guide",
                                "license": {
                                    "status": "known",
                                    "identifier": "CC0-1.0",
                                },
                                "repository": "example/official-guides",
                                "revision": "0123456789012345678901234567890123456789",
                                "path": "market.md",
                            },
                        }
                    ],
                },
            )

            original_registry_prefix = (
                root / "sources" / "registry.json"
            ).read_text(encoding="utf-8").split(
                '\n  ],\n  "repository_sets":', 1
            )[0]
            imported = import_discovery_reviews(root, review_path=review_path)
            resumed_path = root / ".harvester-cache" / "resumed.json"
            resumed = export_discovery_review_batch(
                root,
                now="2026-08-30T20:04:00Z",
                limit=10,
                after=None,
                output_path=resumed_path,
            )
            registry = json.loads(
                (root / "sources" / "registry.json").read_text(encoding="utf-8")
            )
            registry_text = (root / "sources" / "registry.json").read_text(
                encoding="utf-8"
            )

        self.assertEqual(exported["exported_hits"], 2)
        self.assertEqual(imported["selected_endpoint"], 1)
        self.assertEqual(imported["pending"], 1)
        self.assertEqual(resumed["exported_hits"], 1)
        self.assertEqual(
            [source["id"] for source in registry["sources"]],
            ["existing-official-doc", "official-market-guide"],
        )
        self.assertTrue(
            registry_text.startswith(original_registry_prefix.rstrip() + ","),
            "existing registry bytes were reformatted instead of appending a source",
        )

    def test_invalid_license_leaves_hit_pending_and_duplicate_recurrence_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = prepare_query(root)
            hit = {
                "route": "github-code",
                "url": "https://github.com/example/official-guides/blob/main/market.md",
                "repository": "example/official-guides",
                "path": "market.md",
            }
            import_hits(root, str(batch["batch_id"]), [hit])
            export_path = root / ".harvester-cache" / "discovery.json"
            export_discovery_review_batch(
                root,
                now="2026-08-30T20:02:00Z",
                limit=10,
                after=None,
                output_path=export_path,
            )
            hit_id = json.loads(export_path.read_text(encoding="utf-8"))["hits"][0]["id"]
            review_path = root / ".harvester-cache" / "review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-30T20:03:00Z",
                    "items": [
                        {
                            "hit_id": hit_id,
                            "outcome": "selected_endpoint",
                            "assessed_trust": "official",
                            "license_assessment": {"status": "unknown", "identifier": None},
                            "rationale": (
                                "The page looks relevant, but its reuse and operational "
                                "authority cannot be accepted without a known license."
                            ),
                            "selected_endpoint": {
                                "source_id": "unknown-license-guide",
                                "url": "https://example.test/guide",
                                "adapter": "document",
                                "tier": "T1",
                                "trust": "official",
                                "authority": "official-operational-guide",
                                "license": {"status": "unknown", "identifier": None},
                                "revision": "reviewed-2026-08-30",
                            },
                        }
                    ],
                },
            )
            with self.assertRaisesRegex(DiscoveryReviewError, "known license"):
                import_discovery_reviews(root, review_path=review_path)
            with open_runtime_store(root) as store:
                self.assertEqual(store.discovery_review_metrics()["pending"], 1)

            next_cycle = export_query_batch(
                root,
                now="2026-09-01T20:00:00Z",
                cycle_id="daily-life-pilot-2",
                limit=10,
                output_path=root / ".harvester-cache" / "next-query.json",
            )
            import_hits(
                root,
                str(next_cycle["batch_id"]),
                [hit],
                executed_at="2026-09-01T20:01:00Z",
            )
            with open_runtime_store(root) as store:
                metrics = store.discovery_review_metrics()
                record = store.discovery_hit(hit_id)

        self.assertEqual(metrics["unique_hits"], 1)
        self.assertEqual(metrics["pending"], 1)
        self.assertEqual(record["seen_count"], 2)


if __name__ == "__main__":
    unittest.main()
