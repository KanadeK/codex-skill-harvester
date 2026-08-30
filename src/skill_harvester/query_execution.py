from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

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
        query_tokens = shlex.split(text, posix=True)
        if not query_tokens:
            raise QueryExecutionError("GitHub query must not be empty")
        if route == "github-code":
            command = [
                self.executable,
                "search",
                "code",
                "--limit",
                "1",
                "--json",
                "path,repository,url",
                "--",
                *query_tokens,
            ]
        elif route == "github-repository":
            command = [
                self.executable,
                "search",
                "repos",
                "--limit",
                "1",
                "--json",
                "fullName,updatedAt,url",
                "--",
                *query_tokens,
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


def _discovery_hit(route: str, match: dict[str, Any]) -> dict[str, str]:
    url = match.get("url")
    parsed = urlparse(url) if isinstance(url, str) else None
    if (
        parsed is None
        or parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise QueryExecutionError("GitHub query returned an invalid result URL")
    raw_repository = match.get("repository")
    if isinstance(raw_repository, dict):
        repository = raw_repository.get("nameWithOwner") or raw_repository.get(
            "fullName"
        )
    else:
        repository = raw_repository
    if route == "github-repository":
        repository = match.get("fullName") or repository
    if not isinstance(repository, str) or not re.fullmatch(
        r"[^/\s]+/[^/\s]+", repository
    ):
        raise QueryExecutionError("GitHub query result omitted repository identity")
    hit = {"route": route, "url": url, "repository": repository}
    if route == "github-code":
        path = match.get("path")
        if not isinstance(path, str) or not path:
            raise QueryExecutionError("GitHub code result omitted its path")
        hit["path"] = path
    updated_at = match.get("updatedAt")
    if isinstance(updated_at, str) and updated_at:
        hit["updated_at"] = updated_at
    return hit


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
                "discovery_hits": [
                    _discovery_hit(query["route"], match) for match in matches
                ],
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
