from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def document_source(source_id: str = "official-doc") -> dict[str, Any]:
    return {
        "id": source_id,
        "adapter": "document",
        "url": f"https://example.test/{source_id}.md",
        "trust": "official",
        "authority": "vendor-docs",
        "license": {"status": "known", "identifier": "MIT"},
    }
