from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.io import atomic_write_json
from skill_harvester.queries import (
    QueryBatchError,
    export_query_batch,
    import_query_results,
)

from _support import document_source, write_registry


class QueryBatchTests(unittest.TestCase):
    def test_partial_query_batch_resumes_and_completed_rotation_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            atomic_write_json(
                root / "config" / "topic-bank.json",
                {
                    "schema_version": 1,
                    "topics": [
                        {
                            "id": "software.publish.python-packaging",
                            "domain": "software",
                            "intent": "publish",
                            "source_group": "python-packaging",
                            "queries": [
                                {
                                    "id": "python-build-guide",
                                    "route": "github-code",
                                    "text": "repo:pypa/packaging.python.org build distributions",
                                    "tier_constraint": ["T0", "T1", "T2"],
                                },
                                {
                                    "id": "python-trusted-publishing",
                                    "route": "github-code",
                                    "text": "repo:pypi/warehouse trusted publisher",
                                    "tier_constraint": ["T0", "T1", "T2"],
                                },
                            ],
                        }
                    ],
                },
            )
            first_path = root / ".harvester-cache" / "queries.json"
            first = export_query_batch(
                root,
                now="2026-08-29T09:00:00Z",
                cycle_id="content-production-2026-08-29",
                limit=10,
                output_path=first_path,
            )
            self.assertEqual(first["status"], "changed")
            self.assertEqual(first["exported_queries"], 2)

            result_path = root / ".harvester-cache" / "results.json"
            atomic_write_json(
                result_path,
                {
                    "schema_version": 1,
                    "batch_id": first["batch_id"],
                    "executed_by": "codex-agent-reach",
                    "executed_at": "2026-08-29T09:01:00Z",
                    "results": [
                        {
                            "query_id": "python-build-guide",
                            "status": "completed",
                            "cursor": None,
                            "result_count": 4,
                            "selected_endpoints": [
                                {
                                    "source_id": "pypa-publishing-guide",
                                    "url": "https://raw.githubusercontent.com/pypa/packaging.python.org/main/source/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows.rst",
                                    "adapter": "document",
                                    "tier": "T1",
                                    "trust": "official",
                                    "authority": "official-operational-guide",
                                    "license": {"status": "facts-only", "identifier": None},
                                }
                            ],
                        }
                    ],
                },
            )
            incompatible = json.loads(result_path.read_text(encoding="utf-8"))
            incompatible["results"][0]["selected_endpoints"][0]["tier"] = "T4"
            atomic_write_json(result_path, incompatible)
            with self.assertRaisesRegex(QueryBatchError, "tier constraint"):
                import_query_results(
                    root, batch_id=first["batch_id"], results_path=result_path
                )
            incompatible["results"][0]["selected_endpoints"][0]["tier"] = "T1"
            incompatible["results"][0]["selected_endpoints"][0][
                "url"
            ] = "https://secret@example.test/guide"
            atomic_write_json(result_path, incompatible)
            with self.assertRaisesRegex(QueryBatchError, "credential-free https"):
                import_query_results(
                    root, batch_id=first["batch_id"], results_path=result_path
                )
            incompatible["results"][0]["selected_endpoints"][0][
                "url"
            ] = "https://example.test/guide"
            atomic_write_json(result_path, incompatible)
            partial = import_query_results(
                root, batch_id=first["batch_id"], results_path=result_path
            )
            self.assertEqual(partial["status"], "pending")
            self.assertEqual(partial["pending_queries"], 1)
            self.assertEqual(
                partial["selected_source_ids"], ["pypa-publishing-guide"]
            )

            resumed_path = root / ".harvester-cache" / "resumed.json"
            resumed = export_query_batch(
                root,
                now="2026-08-29T09:02:00Z",
                cycle_id="content-production-2026-08-29",
                limit=10,
                output_path=resumed_path,
            )
            self.assertEqual(resumed["batch_id"], first["batch_id"])
            payload = json.loads(resumed_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [query["id"] for query in payload["queries"]],
                ["python-trusted-publishing"],
            )

            atomic_write_json(
                result_path,
                {
                    "schema_version": 1,
                    "batch_id": first["batch_id"],
                    "executed_by": "codex-agent-reach",
                    "executed_at": "2026-08-29T09:03:00Z",
                    "results": [
                        {
                            "query_id": "python-trusted-publishing",
                            "status": "completed",
                            "cursor": "page-1",
                            "result_count": 3,
                            "selected_endpoints": [],
                        }
                    ],
                },
            )
            completed = import_query_results(
                root, batch_id=first["batch_id"], results_path=result_path
            )
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["actual_queries"], 1)

            no_op_path = root / ".harvester-cache" / "no-op.json"
            no_op = export_query_batch(
                root,
                now="2026-08-29T09:04:00Z",
                cycle_id="content-production-2026-08-29",
                limit=10,
                output_path=no_op_path,
            )
            self.assertEqual(no_op["status"], "no_op")
            self.assertEqual(no_op["exported_queries"], 0)

            next_cycle_path = root / ".harvester-cache" / "next-cycle.json"
            next_cycle = export_query_batch(
                root,
                now="2026-09-05T09:00:00Z",
                cycle_id="content-production-2026-09-05",
                limit=10,
                output_path=next_cycle_path,
            )
            self.assertEqual(next_cycle["status"], "changed")
            self.assertEqual(next_cycle["exported_queries"], 2)
            next_queries = {
                query["id"]: query
                for query in json.loads(
                    next_cycle_path.read_text(encoding="utf-8")
                )["queries"]
            }
            self.assertIsNone(
                next_queries["python-build-guide"]["continuation_cursor"]
            )
            self.assertEqual(
                next_queries["python-trusted-publishing"]["continuation_cursor"],
                "page-1",
            )
            self.assertEqual(
                next_queries["python-trusted-publishing"]["previous_completed_at"],
                "2026-08-29T09:03:00Z",
            )


if __name__ == "__main__":
    unittest.main()
