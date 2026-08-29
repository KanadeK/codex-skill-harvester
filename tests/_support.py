from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_harvester.runtime_store import create_empty_runtime, open_runtime_store


class QueueFetcher:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, dict[str, str]]] = []

    def fetch(self, url: str, headers: dict[str, str]) -> object:
        self.requests.append((url, headers))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def write_registry(root: Path, sources: list[dict[str, Any]]) -> None:
    path = root / "sources" / "registry.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"schema_version": 1, "sources": sources}, indent=2) + "\n",
        encoding="utf-8",
    )
    create_empty_runtime(root)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_source_state(root: Path, source_id: str) -> dict[str, Any]:
    with open_runtime_store(root) as store:
        return store.source_state(source_id)


def runtime_last_successful_run(root: Path) -> str | None:
    with open_runtime_store(root) as store:
        return store.last_successful_run()


def write_runtime_discovery(root: Path, candidate: dict[str, Any], *, queue: str | None = None) -> None:
    value = dict(candidate)
    value.setdefault("source_revision", value["id"])
    value.setdefault("evidence_sha256", "a" * 64)
    with open_runtime_store(root) as store, store.connection:
        store.insert_discovery(value, queue_name=queue or "official-gap")


def write_runtime_state(
    root: Path, *, last_successful_run: str | None, sources: dict[str, dict[str, Any]]
) -> None:
    with open_runtime_store(root) as store:
        store.import_records(
            state={
                "schema_version": 1,
                "last_successful_run": last_successful_run,
                "sources": sources,
            },
            discoveries=[],
            decisions=[],
        )


def document_source(source_id: str = "official-doc") -> dict[str, Any]:
    return {
        "id": source_id,
        "adapter": "document",
        "url": f"https://example.test/{source_id}.md",
        "trust": "official",
        "authority": "vendor-docs",
        "license": {"status": "known", "identifier": "MIT"},
    }
