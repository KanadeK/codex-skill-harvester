from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.io import atomic_write_json
from skill_harvester.runtime_store import (
    RuntimeStoreError,
    import_legacy_runtime,
    open_runtime_store,
)


class RuntimeStoreTests(unittest.TestCase):
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
                },
            )

            report = import_legacy_runtime(root)

            self.assertEqual(report["source_states"], 1)
            self.assertEqual(report["discoveries"], 1)
            self.assertEqual(report["decisions"], 1)
            with open_runtime_store(root) as store:
                self.assertEqual(store.last_successful_run(), "2026-08-29T00:00:00Z")
                self.assertEqual(store.source_state("official-doc")["etag"], '"v1"')
                self.assertEqual(store.discovery("candidate-one")["title"], "Official workflow")
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
