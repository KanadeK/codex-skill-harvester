from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.io import atomic_write_json
from skill_harvester.runtime_store import (
    RuntimeStoreError,
    create_empty_runtime,
    import_legacy_runtime,
    open_runtime_store,
    upgrade_runtime_v3_to_v4,
)

from _support import document_source, write_registry


class RuntimeStoreTests(unittest.TestCase):
    def test_v3_upgrade_atomically_promotes_embedded_query_hits_to_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_empty_runtime(root)
            database = root / "state" / "harvest.sqlite3"
            connection = sqlite3.connect(database)
            query = {
                "id": "market-guide",
                "topic_id": "daily-life.research.fresh-market",
                "source_group": "daily-life-market",
                "tier_constraint": ["T0", "T1", "T2"],
            }
            state = {
                "schema_version": 1,
                "query_id": "market-guide",
                "topic_id": query["topic_id"],
                "last_completed_cycle": "full-campaign-2026-08-30",
                "last_completed_at": "2026-08-30T19:00:00Z",
                "cursor": None,
                "result_count": 1,
                "discovery_hits": [
                    {
                        "route": "github-code",
                        "url": "https://github.com/example/guides/blob/main/market.md",
                        "repository": "example/guides",
                        "path": "market.md",
                    }
                ],
                "selected_endpoints": [],
            }
            connection.execute(
                "INSERT INTO query_batches(id, cycle_id, status, created_at, completed_at, record_json) "
                "VALUES('batch-1', 'full-campaign-2026-08-30', 'completed', ?, ?, ?)",
                (state["last_completed_at"], state["last_completed_at"], json.dumps({"id": "batch-1"})),
            )
            connection.execute(
                "INSERT INTO query_batch_items(batch_id, query_id, status, record_json) "
                "VALUES('batch-1', 'market-guide', 'completed', ?)",
                (json.dumps(query),),
            )
            connection.execute(
                "INSERT INTO query_states(query_id, last_completed_cycle, last_completed_at, "
                "cursor, result_count, selected_endpoint_count, record_json) "
                "VALUES('market-guide', 'full-campaign-2026-08-30', ?, NULL, 1, 0, ?)",
                (state["last_completed_at"], json.dumps(state)),
            )
            connection.execute("DROP TABLE discovery_hit_occurrences")
            connection.execute("DROP TABLE discovery_hits")
            connection.execute(
                "UPDATE metadata SET value = '3' WHERE key = 'schema_version'"
            )
            connection.commit()
            connection.close()

            report = upgrade_runtime_v3_to_v4(root)

            with open_runtime_store(root) as store:
                metrics = store.discovery_review_metrics()
                page = store.discovery_review_page(limit=10, after=None)

        self.assertEqual(report["from_schema"], 3)
        self.assertEqual(report["to_schema"], 4)
        self.assertEqual(report["migrated_hits"], 1)
        self.assertEqual(metrics["pending"], 1)
        self.assertEqual(page["records"][0]["contexts"][0]["query_id"], "market-guide")

    def test_review_page_is_sql_bounded_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            with open_runtime_store(root) as store, store.connection:
                for index in range(1200):
                    candidate = {
                        "schema_version": 3,
                        "id": f"candidate-{index:04d}",
                        "evidence_pack_id": f"pack-{index:04d}",
                        "observation_id": f"observation-{index:04d}",
                        "source_id": "official-doc",
                        "source_group": "github-delivery",
                        "topic_id": "software.validate.delivery",
                        "title": f"Candidate {index}",
                        "trust": "official",
                        "license": {"status": "known"},
                        "canonical_url": f"https://example.test/{index}",
                        "observed_at": "2026-08-29T08:00:00Z",
                        "review_status": "pending",
                        "queue": "official-gap",
                        "fingerprint": {
                            "goal": f"goal {index}",
                            "triggers": ["trigger"],
                            "inputs": ["input"],
                            "outputs": ["output"],
                            "tools": ["tool"],
                            "side_effects": ["read-only"],
                            "platforms": ["github"],
                        },
                        "l3_recall": [],
                    }
                    store.insert_observation(
                        {
                            "schema_version": 2,
                            "id": candidate["observation_id"],
                            "source_id": "official-doc",
                            "source_group": "github-delivery",
                            "topic_id": "software.validate.delivery",
                            "source_revision": str(index),
                            "observed_at": candidate["observed_at"],
                            "trust": "official",
                            "tier": "T1",
                            "authority": "vendor-docs",
                            "canonical_url": candidate["canonical_url"],
                            "evidence_sha256": f"{index:064x}",
                            "license": {"status": "known"},
                        }
                    )
                    store.insert_evidence_pack(
                        {
                            "schema_version": 1,
                            "id": candidate["evidence_pack_id"],
                            "batch_id": None,
                            "outcome": "candidate",
                            "reviewed_by": "codex",
                            "reviewed_at": candidate["observed_at"],
                            "observation_ids": [candidate["observation_id"]],
                            "source_ids": [candidate["source_id"]],
                            "necessary_facts": ["fixture"],
                            "non_obvious_decisions": ["fixture"],
                            "license_assessment": "fixture",
                            "risk": {"level": "standard", "domains": []},
                            "adjacent_capabilities": [],
                            "rationale": "fixture reviewed evidence",
                        }
                    )
                    store.insert_candidate(candidate)

                statements: list[str] = []
                store.connection.set_trace_callback(statements.append)
                first = store.review_page(source_id=None, limit=37, after=None)
                second = store.review_page(
                    source_id=None, limit=37, after=first["next_cursor"]
                )
                plan = store.connection.execute(
                    "EXPLAIN QUERY PLAN SELECT record_json FROM candidates "
                    "WHERE review_status = 'pending' "
                    "ORDER BY queue_rank, trust_rank, observed_at, id LIMIT 38"
                ).fetchall()

            self.assertEqual(len(first["records"]), 37)
            self.assertEqual(len(second["records"]), 37)
            self.assertTrue(set(record["id"] for record in first["records"]).isdisjoint(
                record["id"] for record in second["records"]
            ))
            page_selects = [
                statement
                for statement in statements
                if "FROM candidates" in statement and "record_json" in statement
            ]
            self.assertTrue(page_selects)
            self.assertTrue(all("LIMIT 38" in statement for statement in page_selects))
            self.assertTrue(
                any("candidates_review_page" in str(row[3]) for row in plan)
            )

    def test_import_preserves_legacy_runtime_records_then_sqlite_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_write_json(
                root / "state" / "harvest-state.json",
                {
                    "schema_version": 1,
                    "last_successful_run": "2026-08-29T00:00:00Z",
                    "sources": {
                        "official-doc": {
                            "adapter": "document",
                            "url": "https://example.test/official.md",
                            "etag": '"v1"',
                            "last_modified": None,
                            "cursor": "hash-1",
                            "content_sha256": "a" * 64,
                            "seen_items": {},
                            "material_items": {},
                            "window_item_ids": [],
                            "last_success_at": "2026-08-29T00:00:00Z",
                        }
                    },
                },
            )
            candidate = {
                "schema_version": 1,
                "id": "candidate-one",
                "source_id": "official-doc",
                "source_revision": "hash-1",
                "observed_at": "2026-08-29T00:00:00Z",
                "title": "Official workflow",
                "canonical_url": "https://example.test/official.md",
                "evidence_sha256": "b" * 64,
                "trust": "official",
                "authority": "official-docs",
                "license": {"status": "facts-only", "identifier": None},
                "extracted_facts": [],
                "review_status": "pending",
            }
            atomic_write_json(root / "candidates" / "inbox" / "candidate-one.json", candidate)
            atomic_write_json(
                root / "decisions" / "records" / "candidate-one.json",
                {
                    "schema_version": 2,
                    "candidate_id": "candidate-one",
                    "outcome": "not_promoted",
                    "reactivation_conditions": ["new official evidence"],
                    "fingerprint": {
                        "goal": "review official workflow",
                        "triggers": ["review workflow"],
                        "inputs": ["documentation"],
                        "outputs": ["report"],
                        "tools": ["codex"],
                        "side_effects": ["read-only"],
                        "platforms": ["codex"],
                    },
                },
            )

            report = import_legacy_runtime(root)

            self.assertEqual(report["source_states"], 1)
            self.assertEqual(report["observations"], 1)
            self.assertEqual(report["candidates"], 1)
            self.assertEqual(report["decisions"], 1)
            with open_runtime_store(root) as store:
                self.assertEqual(store.last_successful_run(), "2026-08-29T00:00:00Z")
                self.assertEqual(store.source_state("official-doc")["etag"], '"v1"')
                self.assertEqual(store.observation("candidate-one")["title"], "Official workflow")
                self.assertEqual(store.candidate("candidate-one")["review_status"], "applied")
                self.assertEqual(store.decision_count(), 1)

            atomic_write_json(
                root / "state" / "harvest-state.json",
                {"schema_version": 1, "last_successful_run": "tampered", "sources": {}},
            )
            with open_runtime_store(root) as store:
                self.assertEqual(store.last_successful_run(), "2026-08-29T00:00:00Z")

    def test_import_refuses_to_create_a_second_runtime_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_write_json(
                root / "state" / "harvest-state.json",
                {"schema_version": 1, "last_successful_run": None, "sources": {}},
            )

            import_legacy_runtime(root)

            with self.assertRaisesRegex(RuntimeStoreError, "already exists"):
                import_legacy_runtime(root)


if __name__ == "__main__":
    unittest.main()
