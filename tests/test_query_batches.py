from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.io import atomic_write_json
from skill_harvester.queries import (
    QueryBatchError,
    export_query_batch,
    import_query_results,
    load_topic_bank,
)
from skill_harvester.query_execution import (
    GitHubCliSearch,
    QueryExecutionError,
    execute_github_query_batch,
)
from skill_harvester.runtime_store import open_runtime_store

from _support import document_source, write_registry


class QueryBatchTests(unittest.TestCase):
    def test_github_repository_search_uses_supported_json_fields(self) -> None:
        with patch("skill_harvester.query_execution.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "[]"
            run.return_value.stderr = ""

            GitHubCliSearch().search("github-repository", "agent skills")

        command = run.call_args.args[0]
        self.assertIn("fullName,updatedAt,url", command)
        self.assertNotIn("nameWithOwner", command)

    def test_github_search_preserves_qualifier_token_boundaries(self) -> None:
        with patch("skill_harvester.query_execution.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "[]"
            run.return_value.stderr = ""

            GitHubCliSearch().search(
                "github-code",
                "repo:duckdb/duckdb-web path:docs/current DuckDB concurrency inspect",
            )

        command = run.call_args.args[0]
        separator = command.index("--")
        self.assertEqual(
            command[separator + 1 :],
            [
                "repo:duckdb/duckdb-web",
                "path:docs/current",
                "DuckDB",
                "concurrency",
                "inspect",
            ],
        )

    def test_partial_query_batch_resumes_and_completed_rotation_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(root, [document_source()])
            atomic_write_json(
                root / "config" / "topic-bank.json",
                {
                    "schema_version": 2,
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
                    "operations": [],
                    "query_matrices": [],
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
                            "discovery_hits": [
                                {
                                    "route": "github-code",
                                    "url": "https://github.com/pypa/packaging.python.org/blob/main/source/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows.rst",
                                    "repository": "pypa/packaging.python.org",
                                    "path": "source/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows.rst",
                                }
                            ],
                            "selected_endpoints": [],
                        }
                    ],
                },
            )
            partial = import_query_results(
                root, batch_id=first["batch_id"], results_path=result_path
            )
            self.assertEqual(partial["status"], "pending")
            self.assertEqual(partial["pending_queries"], 1)
            self.assertEqual(
                partial["selected_source_ids"], []
            )
            self.assertEqual(partial["discovery_hits"], 1)
            with open_runtime_store(root) as store:
                state = json.loads(
                    store.connection.execute(
                        "SELECT record_json FROM query_states WHERE query_id = ?",
                        ("python-build-guide",),
                    ).fetchone()[0]
                )
            self.assertEqual(
                state["discovery_hits"][0]["repository"],
                "pypa/packaging.python.org",
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
                    "executed_at": "2026-08-29T09:02:30Z",
                    "results": [
                        {
                            "query_id": "python-trusted-publishing",
                            "status": "failed",
                            "error": "GitHub code-search rate limit reached",
                            "cursor": None,
                            "result_count": 0,
                            "selected_endpoints": [],
                        }
                    ],
                },
            )
            checkpoint = import_query_results(
                root, batch_id=first["batch_id"], results_path=result_path
            )
            self.assertEqual(checkpoint["status"], "pending")
            self.assertEqual(checkpoint["failed_queries"], 1)

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
            summary_path = (
                root / "runs" / "content-production-2026-08-29-queries.json"
            )
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["aggregation"], "cycle")
            self.assertEqual(summary["query_attempts"], 3)
            self.assertEqual(summary["completed_queries"], 2)
            self.assertEqual(summary["failed_queries"], 1)
            self.assertEqual(summary["pending_queries"], 0)
            self.assertEqual(summary["discovery_hits"], 1)
            self.assertEqual(summary["discovery_review"]["pending"], 1)
            self.assertEqual(len(list((root / "runs").glob("*-queries.json"))), 1)

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

    def test_topic_matrix_expands_domain_intent_queries_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            atomic_write_json(
                root / "config" / "topic-bank.json",
                {
                    "schema_version": 2,
                    "topics": [],
                    "operations": [
                        {
                            "id": "build",
                            "intent": "create",
                            "text": "build reproducibly",
                        },
                        {
                            "id": "debug",
                            "intent": "diagnose",
                            "text": "debug failures",
                        },
                    ],
                    "query_matrices": [
                        {
                            "id": "container-delivery",
                            "domain": "software",
                            "source_group": "containers-docker",
                            "route": "github-code",
                            "scope": "repo:docker/docs",
                            "tier_constraint": ["T0", "T1", "T2"],
                            "subjects": [
                                {"id": "images", "text": "Docker images"},
                                {"id": "compose", "text": "Docker Compose"},
                            ],
                            "operation_ids": ["build", "debug"],
                        }
                    ],
                },
            )

            queries = load_topic_bank(root)

        self.assertEqual(len(queries), 4)
        self.assertEqual(
            [query["id"] for query in queries],
            [
                "container-delivery-images-build",
                "container-delivery-images-debug",
                "container-delivery-compose-build",
                "container-delivery-compose-debug",
            ],
        )
        self.assertEqual(queries[1]["intent"], "diagnose")
        self.assertEqual(
            queries[1]["topic_id"], "software.diagnose.container-delivery"
        )
        self.assertEqual(
            queries[1]["text"],
            "repo:docker/docs Docker images debug failures",
        )

    def test_github_query_executor_checkpoints_on_first_failure_without_raw_bodies(
        self,
    ) -> None:
        class FakeSearch:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def search(self, route: str, text: str) -> list[dict[str, object]]:
                self.calls.append(text)
                if len(self.calls) == 2:
                    raise QueryExecutionError(
                        "GitHub code-search rate limit reached"
                    )
                return [
                    {
                        "url": "https://github.com/docker/docs/blob/main/example.md",
                        "path": "example.md",
                        "repository": {"nameWithOwner": "docker/docs"},
                    }
                ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "query-batch.json"
            output_path = root / "query-results.json"
            atomic_write_json(
                input_path,
                {
                    "schema_version": 1,
                    "batch_id": "batch-1",
                    "cycle_id": "full-campaign-2026-08-30",
                    "queries": [
                        {
                            "id": "query-one",
                            "route": "github-code",
                            "text": "repo:docker/docs build cache",
                        },
                        {
                            "id": "query-two",
                            "route": "github-code",
                            "text": "repo:docker/docs debug build",
                        },
                        {
                            "id": "query-three",
                            "route": "web",
                            "text": "site:docs.docker.com deploy containers",
                        },
                        {
                            "id": "query-four",
                            "route": "github-code",
                            "text": "repo:docker/docs validate build",
                        },
                    ],
                },
            )

            report = execute_github_query_batch(
                input_path=input_path,
                output_path=output_path,
                executed_at="2026-08-30T13:00:00Z",
                executor=FakeSearch(),
                limit=10,
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(report["attempted_queries"], 2)
        self.assertEqual(report["completed_queries"], 1)
        self.assertEqual(report["failed_queries"], 1)
        self.assertEqual(report["unsupported_queries"], 1)
        self.assertEqual(report["remaining_supported_queries"], 1)
        self.assertTrue(report["checkpointed"])
        self.assertEqual(payload["executed_by"], "codex-agent-reach")
        self.assertEqual([item["status"] for item in payload["results"]], ["completed", "failed"])
        self.assertEqual(payload["results"][0]["result_count"], 1)
        self.assertEqual(
            payload["results"][0]["discovery_hits"],
            [
                {
                    "route": "github-code",
                    "url": "https://github.com/docker/docs/blob/main/example.md",
                    "repository": "docker/docs",
                    "path": "example.md",
                }
            ],
        )
        self.assertEqual(payload["results"][0]["selected_endpoints"], [])
        self.assertNotIn("body", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
