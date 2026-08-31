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
    normalized_sources = []
    for source in sources:
        value = dict(source)
        value.setdefault(
            "tier",
            "T2"
            if value.get("trust") == "official"
            else "T3"
            if value.get("trust") == "representative"
            else "T4",
        )
        normalized_sources.append(value)
    path = root / "sources" / "registry.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"schema_version": 1, "sources": normalized_sources}, indent=2) + "\n",
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
    observation_id = f"observation-{value['id']}"
    observation = {
        "schema_version": 3,
        "id": observation_id,
        "source_id": value["source_id"],
        "source_group": value.get("source_group", "fixture-group"),
        "topic_id": value.get("topic_id", "fixture.topic"),
        "source_revision": value["source_revision"],
        "observed_at": value["observed_at"],
        "title": value["title"],
        "canonical_url": value["canonical_url"],
        "evidence_sha256": value["evidence_sha256"],
        "trust": value["trust"],
        "tier": value.get(
            "tier",
            "T2"
            if value["trust"] == "official"
            else "T3"
            if value["trust"] == "representative"
            else "T4",
        ),
        "authority": value.get("authority", "fixture-authority"),
        "license": value["license"],
        "extracted_facts": value.get("extracted_facts", []),
    }
    queue_name = queue or "official-gap"
    flags = {
        "published_impact": queue_name == "urgent-impact",
        "operational_authority": queue_name == "official-gap",
        "reactivated": queue_name == "reactivation",
        "aged_backlog": queue_name == "aged-backlog",
    }
    normalized_candidate = {
        **value,
        "schema_version": 3,
        "evidence_pack_id": f"fixture-pack-{value['id']}",
        "observation_id": observation_id,
        "source_group": observation["source_group"],
        "topic_id": observation["topic_id"],
        "fingerprint": value.get(
            "fingerprint",
            {
                "goal": f"review {value['id']}",
                "triggers": ["review fixture"],
                "inputs": ["fixture"],
                "outputs": ["report"],
                "tools": ["test"],
                "side_effects": ["read-only"],
                "platforms": ["local"],
            },
        ),
        "l3_recall": value.get("l3_recall", []),
        **flags,
    }
    with open_runtime_store(root) as store, store.connection:
        store.insert_observation(observation)
        store.insert_evidence_pack(
            {
                "schema_version": 1,
                "id": normalized_candidate["evidence_pack_id"],
                "batch_id": None,
                "outcome": "candidate",
                "reviewed_by": "codex",
                "reviewed_at": value["observed_at"],
                "observation_ids": [observation_id],
                "source_ids": [value["source_id"]],
                "necessary_facts": ["Fixture evidence."],
                "non_obvious_decisions": ["Fixture decision."],
                "license_assessment": "Fixture license.",
                "risk": {"level": "standard", "domains": []},
                "adjacent_capabilities": [],
                "rationale": "Fixture-only reviewed evidence for deterministic tests.",
            }
        )
        store.insert_candidate(normalized_candidate)


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


def document_source(
    source_id: str = "official-doc", *, trust: str = "official", tier: str = "T1"
) -> dict[str, Any]:
    return {
        "id": source_id,
        "adapter": "document",
        "url": f"https://example.test/{source_id}.md",
        "trust": trust,
        "tier": tier,
        "authority": "vendor-docs",
        "license": {"status": "known", "identifier": "MIT"},
    }


def workflow_source(
    source_id: str = "workflow-doc",
    *,
    trust: str = "official",
    operational_authority: bool = True,
    **workflow_flags: bool,
) -> dict[str, Any]:
    source = document_source(source_id)
    source["trust"] = trust
    source["workflow_signal"] = {
        "operational_authority": operational_authority,
        "fingerprint": {
            "goal": f"verify {source_id} delivery evidence",
            "triggers": [f"verify {source_id}"],
            "inputs": ["repository", "release"],
            "outputs": ["evidence report"],
            "tools": ["gh"],
            "side_effects": ["network-read"],
            "platforms": ["github"],
        },
        **workflow_flags,
    }
    return source


def scan_context(
    *source_ids: str,
    source_group: str = "github-delivery",
    topic_id: str = "software.validate.delivery",
) -> dict[str, dict[str, str]]:
    return {
        source_id: {"source_group": source_group, "topic_id": topic_id}
        for source_id in source_ids
    }
