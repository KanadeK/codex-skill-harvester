from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.io import atomic_write_json
from skill_harvester.runtime_store import open_runtime_store
from skill_harvester.semantic import (
    SemanticReviewError,
    export_semantic_batch,
    import_semantic_review,
)
from skill_harvester.sources import FetchResponse, run_scan

from _support import QueueFetcher, document_source, scan_context, workflow_source, write_registry


FINGERPRINT = {
    "goal": "validate Python release artifacts before publication",
    "triggers": ["check whether these Python distributions are ready to publish"],
    "inputs": ["pyproject.toml", "sdist", "wheel", "publishing workflow"],
    "outputs": ["release readiness report"],
    "tools": ["python", "archive inspection"],
    "side_effects": ["local-read", "temporary-local-write"],
    "platforms": ["python packaging", "github actions"],
}


def review_item(observation_id: str, **flags: bool) -> dict[str, object]:
    return {
        "observation_ids": [observation_id],
        "outcome": "candidate",
        "necessary_facts": [
            "Build and publish are separate stages.",
            "A release should contain an sdist and applicable wheels.",
        ],
        "non_obvious_decisions": [
            "Validate archive identity and workflow boundaries without publishing."
        ],
        "fingerprint": FINGERPRINT,
        "license_assessment": "Facts paraphrased from known-license official documentation.",
        "risk": {"level": "standard", "domains": []},
        "adjacent_capabilities": ["github-release-evidence:audit-github-release"],
        "rationale": (
            "The source describes a repeatable pre-publication validation goal with "
            "clear artifacts, checks, and a report boundary distinct from publishing."
        ),
        "operational_authority": True,
        **flags,
    }


class FunnelPipelineTests(unittest.TestCase):
    def test_corrupt_evidence_cache_is_refetched_and_semantic_text_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = document_source("large-guide")
            write_registry(root, [source])
            body = b"# Large guide\n" + (b"x" * 130_000)
            first_fetcher = QueueFetcher(
                FetchResponse(200, source["url"], {"etag": '"v1"'}, body)
            )
            run_scan(
                root,
                first_fetcher,
                now="2026-08-29T07:00:00Z",
                source_context=scan_context("large-guide"),
            )
            with open_runtime_store(root) as store:
                observation = next(store.observations())
            cache = root / observation["cache_path"]
            cache.write_bytes(b"corrupt cache")

            second_fetcher = QueueFetcher(
                FetchResponse(200, source["url"], {"etag": '"v1"'}, body)
            )
            replay = run_scan(
                root,
                second_fetcher,
                now="2026-08-29T07:01:00Z",
                source_context=scan_context("large-guide"),
            )

            self.assertEqual(replay["status"], "no_op")
            self.assertNotIn("If-None-Match", second_fetcher.requests[0][1])
            self.assertTrue(cache.is_file())
            export_path = root / ".harvester-cache" / "bounded.json"
            export_semantic_batch(
                root,
                now="2026-08-29T07:02:00Z",
                limit=1,
                output_path=export_path,
            )
            evidence = json.loads(export_path.read_text(encoding="utf-8"))[
                "observations"
            ][0]["evidence"]
            self.assertEqual(len(evidence["text"]), 120_000)
            self.assertTrue(evidence["truncated"])

    def test_semantic_export_rejects_cache_path_outside_temporary_evidence_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = document_source("unsafe-cache")
            write_registry(root, [source])
            run_scan(
                root,
                QueueFetcher(FetchResponse(200, source["url"], {}, b"# Safe")),
                now="2026-08-29T07:10:00Z",
                source_context=scan_context("unsafe-cache"),
            )
            outside = root / "outside.txt"
            outside.write_text("must not be read", encoding="utf-8")
            with open_runtime_store(root) as store, store.connection:
                row = store.connection.execute(
                    "SELECT id, record_json FROM observations"
                ).fetchone()
                record = json.loads(row["record_json"])
                record["cache_path"] = "../outside.txt"
                store.connection.execute(
                    "UPDATE observations SET record_json = ? WHERE id = ?",
                    (json.dumps(record), row["id"]),
                )

            with self.assertRaisesRegex(SemanticReviewError, "evidence cache path"):
                export_semantic_batch(
                    root,
                    now="2026-08-29T07:11:00Z",
                    limit=1,
                    output_path=root / ".harvester-cache" / "unsafe.json",
                )

    def test_workflow_signal_is_hint_only_and_unhinted_source_enters_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hinted = workflow_source("hinted-doc")
            unhinted = document_source("unhinted-doc")
            write_registry(root, [hinted, unhinted])

            report = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, hinted["url"], {"etag": '"v1"'}, b"# Hint only"),
                    FetchResponse(
                        200,
                        unhinted["url"],
                        {"etag": '"v1"'},
                        b"# Build and validate distributions\n\nInspect the artifacts before upload.",
                    ),
                ),
                now="2026-08-29T08:00:00Z",
                source_context=scan_context("hinted-doc", "unhinted-doc"),
            )

            self.assertEqual(report["metrics"]["observations_inserted"], 2)
            self.assertEqual(report["metrics"]["normalized_candidates"], 0)
            with open_runtime_store(root) as store:
                self.assertEqual(store.candidate_count(), 0)

            export_path = root / ".harvester-cache" / "semantic.json"
            exported = export_semantic_batch(
                root, now="2026-08-29T08:01:00Z", limit=10, output_path=export_path
            )

            self.assertEqual(exported["status"], "changed")
            self.assertEqual(exported["exported_observations"], 2)
            payload = json.loads(export_path.read_text(encoding="utf-8"))
            by_source = {item["source_id"]: item for item in payload["observations"]}
            self.assertIn("workflow_hint", by_source["hinted-doc"])
            self.assertTrue(by_source["hinted-doc"]["workflow_hint"]["non_authoritative"])
            self.assertNotIn("workflow_hint", by_source["unhinted-doc"])

    def test_reviewed_evidence_pack_creates_candidate_with_l2_l3_and_topic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = document_source("python-publish-guide")
            write_registry(root, [source])
            (root / "catalog").mkdir()
            atomic_write_json(
                root / "catalog" / "capabilities.json",
                {
                    "schema_version": 2,
                    "internal": [
                        {"id": "internal:release-readiness", "fingerprint": FINGERPRINT}
                    ],
                    "external": [],
                },
            )
            run_scan(
                root,
                QueueFetcher(
                    FetchResponse(
                        200,
                        source["url"],
                        {"etag": '"v1"'},
                        b"# Publishing distributions\n\nBuild once, validate, then publish.",
                    )
                ),
                now="2026-08-29T08:05:00Z",
                source_context=scan_context(
                    "python-publish-guide",
                    source_group="python-packaging",
                    topic_id="software.publish.python-packaging",
                ),
            )
            export_path = root / ".harvester-cache" / "semantic.json"
            exported = export_semantic_batch(
                root, now="2026-08-29T08:06:00Z", limit=10, output_path=export_path
            )
            observation_id = json.loads(export_path.read_text(encoding="utf-8"))[
                "observations"
            ][0]["id"]
            review_path = root / ".harvester-cache" / "review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "batch_id": exported["batch_id"],
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-29T08:07:00Z",
                    "items": [review_item(observation_id)],
                },
            )

            imported = import_semantic_review(
                root, batch_id=exported["batch_id"], review_path=review_path
            )

            self.assertEqual(imported["normalized_candidates"], 1)
            self.assertEqual(imported["l3_recalls"], 1)
            with open_runtime_store(root) as store:
                candidate = next(store.candidates())
                pack = store.evidence_pack(candidate["evidence_pack_id"])
            self.assertEqual(candidate["topic_id"], "software.publish.python-packaging")
            self.assertEqual(set(candidate["fingerprint"]), set(FINGERPRINT))
            self.assertEqual(candidate["l3_recall"][0]["id"], "internal:release-readiness")
            self.assertEqual(candidate["queue"], "official-gap")
            self.assertEqual(pack["observation_ids"], [observation_id])
            self.assertEqual(pack["reviewed_by"], "codex")

    def test_partial_review_resumes_same_batch_and_then_becomes_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [document_source("first"), document_source("second")]
            write_registry(root, sources)
            (root / "catalog").mkdir()
            atomic_write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 2, "internal": [], "external": []},
            )
            run_scan(
                root,
                QueueFetcher(
                    *[
                        FetchResponse(200, source["url"], {}, f"# {source['id']}".encode())
                        for source in sources
                    ]
                ),
                now="2026-08-29T08:10:00Z",
                source_context=scan_context("first", "second"),
            )
            first_export_path = root / ".harvester-cache" / "first-export.json"
            first = export_semantic_batch(
                root, now="2026-08-29T08:11:00Z", limit=10, output_path=first_export_path
            )
            ids = [
                item["id"]
                for item in json.loads(first_export_path.read_text(encoding="utf-8"))[
                    "observations"
                ]
            ]
            first_review = root / ".harvester-cache" / "first-review.json"
            atomic_write_json(
                first_review,
                {
                    "schema_version": 1,
                    "batch_id": first["batch_id"],
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-29T08:12:00Z",
                    "items": [review_item(ids[0])],
                },
            )
            partial = import_semantic_review(
                root, batch_id=first["batch_id"], review_path=first_review
            )
            self.assertEqual(partial["status"], "pending")
            self.assertEqual(partial["pending_observations"], 1)

            resumed_path = root / ".harvester-cache" / "resumed.json"
            resumed = export_semantic_batch(
                root, now="2026-08-29T08:13:00Z", limit=10, output_path=resumed_path
            )
            self.assertEqual(resumed["batch_id"], first["batch_id"])
            resumed_ids = [
                item["id"]
                for item in json.loads(resumed_path.read_text(encoding="utf-8"))[
                    "observations"
                ]
            ]
            self.assertEqual(resumed_ids, [ids[1]])

            second_review = root / ".harvester-cache" / "second-review.json"
            atomic_write_json(
                second_review,
                {
                    "schema_version": 1,
                    "batch_id": first["batch_id"],
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-29T08:14:00Z",
                    "items": [
                        {
                            "observation_ids": [ids[1]],
                            "outcome": "not_promoted",
                            "necessary_facts": ["The page exposes a single command only."],
                            "non_obvious_decisions": [],
                            "license_assessment": "Known-license official documentation.",
                            "risk": {"level": "standard", "domains": []},
                            "adjacent_capabilities": [],
                            "rationale": (
                                "This evidence does not establish a repeatable workflow with "
                                "a distinct goal, inputs, outputs, and non-obvious decisions."
                            ),
                            "reactivation_conditions": [
                                "Reconsider when official workflow documentation adds a multi-step task."
                            ],
                        }
                    ],
                },
            )
            completed = import_semantic_review(
                root, batch_id=first["batch_id"], review_path=second_review
            )
            self.assertEqual(completed["status"], "completed")

            no_op_path = root / ".harvester-cache" / "noop.json"
            no_op = export_semantic_batch(
                root, now="2026-08-29T08:15:00Z", limit=10, output_path=no_op_path
            )
            self.assertEqual(no_op["status"], "no_op")
            self.assertEqual(no_op["exported_observations"], 0)

    def test_all_five_queues_are_assigned_after_content_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [
                document_source("urgent"),
                document_source("official"),
                document_source("reactivated", trust="representative"),
                document_source("novel", trust="representative"),
                document_source("aged", trust="representative"),
            ]
            write_registry(root, sources)
            (root / "catalog").mkdir()
            atomic_write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 2, "internal": [], "external": []},
            )
            run_scan(
                root,
                QueueFetcher(
                    *[
                        FetchResponse(200, source["url"], {}, f"# {source['id']}".encode())
                        for source in sources
                    ]
                ),
                now="2026-08-29T08:20:00Z",
                source_context=scan_context(*(source["id"] for source in sources)),
            )
            export_path = root / ".harvester-cache" / "queues.json"
            exported = export_semantic_batch(
                root, now="2026-08-29T08:21:00Z", limit=10, output_path=export_path
            )
            observations = json.loads(export_path.read_text(encoding="utf-8"))[
                "observations"
            ]
            by_source = {item["source_id"]: item["id"] for item in observations}
            review_path = root / ".harvester-cache" / "queue-review.json"
            atomic_write_json(
                review_path,
                {
                    "schema_version": 1,
                    "batch_id": exported["batch_id"],
                    "reviewed_by": "codex",
                    "reviewed_at": "2026-08-29T08:22:00Z",
                    "items": [
                        review_item(by_source["urgent"], published_impact=True),
                        review_item(by_source["official"]),
                        review_item(
                            by_source["reactivated"],
                            operational_authority=False,
                            reactivated=True,
                        ),
                        review_item(by_source["novel"], operational_authority=False),
                        review_item(
                            by_source["aged"],
                            operational_authority=False,
                            aged_backlog=True,
                        ),
                    ],
                },
            )
            import_semantic_review(
                root, batch_id=exported["batch_id"], review_path=review_path
            )

            with open_runtime_store(root) as store:
                queues = {
                    candidate["source_id"]: candidate["queue"]
                    for candidate in store.candidates()
                }
            self.assertEqual(
                queues,
                {
                    "urgent": "urgent-impact",
                    "official": "official-gap",
                    "reactivated": "reactivation",
                    "novel": "novel-discovery",
                    "aged": "aged-backlog",
                },
            )


if __name__ == "__main__":
    unittest.main()
