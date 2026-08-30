from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Protocol

from .io import atomic_write_json, load_json


class QueryExecutionError(RuntimeError):
    pass


class QuerySearch(Protocol):
    def search(self, route: str, text: str) -> list[dict[str, Any]]: ...


class GitHubCliSearch:
    def __init__(
        self,
        *,
        executable: str = "gh",
        timeout: float = 30.0,
    ) -> None:
        self.executable = executable
        self.timeout = timeout

    def search(self, route: str, text: str) -> list[dict[str, Any]]:
        if route == "github-code":
            command = [
                self.executable,
                "search",
                "code",
                text,
                "--limit",
                "1",
                "--json",
                "path,repository,url",
            ]
        elif route == "github-repository":
            command = [
                self.executable,
                "search",
                "repos",
                text,
                "--limit",
                "1",
                "--json",
                "nameWithOwner,updatedAt,url",
            ]
        else:
            raise QueryExecutionError(f"unsupported GitHub query route: {route}")
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise QueryExecutionError(
                f"GitHub query timed out after {self.timeout} seconds"
            ) from error
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "GitHub query failed"
            raise QueryExecutionError(detail[:1000])
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise QueryExecutionError("GitHub query returned invalid JSON") from error
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise QueryExecutionError("GitHub query result must be a JSON list")
        return result


def execute_github_query_batch(
    *,
    input_path: Path,
    output_path: Path,
    executed_at: str,
    executor: QuerySearch,
    limit: int,
) -> dict[str, Any]:
    if limit < 1:
        raise QueryExecutionError("query execution limit must be positive")
    payload = load_json(input_path)
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or not isinstance(payload.get("batch_id"), str)
        or not payload["batch_id"]
        or not isinstance(payload.get("queries"), list)
    ):
        raise QueryExecutionError("query batch is invalid")
    supported_queries = [
        query
        for query in payload["queries"]
        if isinstance(query, dict)
        and query.get("route") in {"github-code", "github-repository"}
    ]
    selected_queries = supported_queries[:limit]
    if not selected_queries:
        raise QueryExecutionError("query batch has no executable GitHub queries")
    results: list[dict[str, Any]] = []
    checkpointed = False
    for query in selected_queries:
        query_id = query.get("id")
        text = query.get("text")
        if not isinstance(query_id, str) or not isinstance(text, str) or not text:
            raise QueryExecutionError("GitHub query record is invalid")
        try:
            matches = executor.search(query["route"], text)
        except QueryExecutionError as error:
            results.append(
                {
                    "query_id": query_id,
                    "status": "failed",
                    "error": str(error),
                    "cursor": query.get("continuation_cursor"),
                    "result_count": 0,
                    "selected_endpoints": [],
                }
            )
            checkpointed = True
            break
        results.append(
            {
                "query_id": query_id,
                "status": "completed",
                "cursor": None,
                "result_count": len(matches),
                "selected_endpoints": [],
            }
        )
    output = {
        "schema_version": 1,
        "batch_id": payload["batch_id"],
        "executed_by": "codex-agent-reach",
        "executed_at": executed_at,
        "results": results,
    }
    atomic_write_json(output_path, output)
    completed = sum(result["status"] == "completed" for result in results)
    failed = len(results) - completed
    return {
        "batch_id": payload["batch_id"],
        "attempted_queries": len(results),
        "completed_queries": completed,
        "failed_queries": failed,
        "unsupported_queries": len(payload["queries"]) - len(supported_queries),
        "remaining_supported_queries": len(supported_queries) - len(results),
        "checkpointed": checkpointed,
        "output": str(output_path),
    }
