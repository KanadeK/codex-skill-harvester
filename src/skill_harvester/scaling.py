from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path
from time import perf_counter
from typing import Any

from .io import load_json
from .runtime_store import RuntimeStoreError, open_runtime_store, runtime_store_path


TRIGGER_FIELDS = (
    "candidate_records",
    "candidate_lifecycle_files",
    "harvest_state_bytes",
    "seen_source_items",
)


class ScalePolicyError(ValueError):
    pass


def _positive_integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ScalePolicyError(f"{label} must be a positive integer")
    return value


def validate_scale_policy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ScalePolicyError("scale policy must use schema_version 1")
    if value.get("backend") not in {"git-json-v1", "sqlite-v1"}:
        raise ScalePolicyError("scale policy backend must be git-json-v1 or sqlite-v1")
    review_batch = value.get("review_batch")
    if not isinstance(review_batch, dict):
        raise ScalePolicyError("scale policy review batch is missing")
    default = _positive_integer(review_batch.get("default"), "review batch default")
    maximum = _positive_integer(review_batch.get("maximum"), "review batch maximum")
    if default > maximum:
        raise ScalePolicyError("review batch default cannot exceed maximum")

    triggers = value.get("migration_triggers")
    if not isinstance(triggers, dict) or set(triggers) != {
        *TRIGGER_FIELDS,
        "full_validation_seconds",
    }:
        raise ScalePolicyError("scale policy migration triggers are incomplete")
    for field in TRIGGER_FIELDS:
        _positive_integer(triggers[field], f"migration trigger {field}")
    validation_seconds = triggers["full_validation_seconds"]
    if (
        not isinstance(validation_seconds, (int, float))
        or isinstance(validation_seconds, bool)
        or validation_seconds <= 0
    ):
        raise ScalePolicyError(
            "migration trigger full_validation_seconds must be positive"
        )

    targets = value.get("projection_targets")
    if not isinstance(targets, dict):
        raise ScalePolicyError("scale policy projection targets are missing")
    for field in ("candidate_records", "source_records"):
        values = targets.get(field)
        if (
            not isinstance(values, list)
            or not values
            or any(
                not isinstance(item, int) or isinstance(item, bool) or item <= 0
                for item in values
            )
            or values != sorted(set(values))
        ):
            raise ScalePolicyError(
                f"projection target {field} must be sorted unique positive integers"
            )
    _positive_integer(
        value.get("benchmark_fixture_records"), "benchmark fixture records"
    )
    return value


def load_scale_policy(root: Path) -> dict[str, Any]:
    return validate_scale_policy(load_json(root / "config" / "scale-policy.json"))


def inventory_repository(root: Path) -> dict[str, Any]:
    path = runtime_store_path(root)
    if not path.is_file():
        raise ScalePolicyError("runtime SQLite store is missing")
    try:
        with open_runtime_store(root) as store:
            candidates = list(store.discoveries())
            decisions = list(store.decisions())
            source_states = list(store.source_states())
    except RuntimeStoreError as error:
        raise ScalePolicyError(str(error)) from error

    candidate_bytes = sum(len(json.dumps(value, ensure_ascii=False)) for value in candidates)
    decision_bytes = sum(len(json.dumps(value, ensure_ascii=False)) for value in decisions)
    seen_items = 0
    material_items = 0
    for _, source in source_states:
        if not isinstance(source, dict):
            raise ScalePolicyError("harvest source state is invalid")
        seen = source.get("seen_items", {})
        material = source.get("material_items", {})
        if not isinstance(seen, dict) or not isinstance(material, dict):
            raise ScalePolicyError("harvest item state is invalid")
        seen_items += len(seen)
        material_items += len(material)

    lifecycle_bytes = path.stat().st_size
    candidate_count = len(candidates)
    return {
        "schema_version": 1,
        "candidate_records": candidate_count,
        "candidate_lifecycle_files": 1,
        "candidate_bytes": candidate_bytes,
        "reviewed_decision_bytes": 0,
        "applied_decision_bytes": decision_bytes,
        "candidate_lifecycle_bytes": lifecycle_bytes,
        "candidate_lifecycle_average_bytes": (
            lifecycle_bytes / candidate_count if candidate_count else 0
        ),
        "harvest_state_bytes": path.stat().st_size,
        "seen_source_items": seen_items,
        "material_source_items": material_items,
    }


def evaluate_migration_triggers(
    inventory: dict[str, Any],
    policy_value: Any,
    *,
    full_validation_seconds: float | None = None,
) -> list[str]:
    policy = validate_scale_policy(policy_value)
    thresholds = policy["migration_triggers"]
    triggered = [
        field
        for field in TRIGGER_FIELDS
        if inventory[field] >= thresholds[field]
    ]
    if (
        full_validation_seconds is not None
        and full_validation_seconds >= thresholds["full_validation_seconds"]
    ):
        triggered.append("full_validation_seconds")
    return sorted(triggered)


def project_storage(
    inventory: dict[str, Any], policy_value: Any
) -> dict[str, list[dict[str, int]]]:
    policy = validate_scale_policy(policy_value)
    lifecycle_average = inventory["candidate_lifecycle_average_bytes"]
    seen_items = inventory["seen_source_items"]
    state_bytes_per_item = (
        inventory["harvest_state_bytes"] / seen_items if seen_items else 0
    )
    return {
        "candidate_records": [
            {
                "records": target,
                "lifecycle_files": 1,
                "estimated_payload_bytes": round(lifecycle_average * target),
            }
            for target in policy["projection_targets"]["candidate_records"]
        ],
        "source_records": [
            {
                "records": target,
                "estimated_state_bytes": round(state_bytes_per_item * target),
            }
            for target in policy["projection_targets"]["source_records"]
        ],
    }


def benchmark_json_lifecycle(records: int) -> dict[str, Any]:
    _positive_integer(records, "benchmark records")
    with tempfile.TemporaryDirectory(prefix="skill-harvester-scale-") as directory:
        root = Path(directory)
        groups = ("candidates", "reviewed", "decisions")
        for group in groups:
            (root / group).mkdir()

        write_started = perf_counter()
        for index in range(records):
            record_id = f"candidate-{index:08d}"
            payloads = {
                "candidates": {
                    "schema_version": 1,
                    "id": record_id,
                    "source_id": "benchmark-source",
                    "review_status": "pending",
                    "evidence_sha256": "a" * 64,
                },
                "reviewed": {
                    "schema_version": 2,
                    "candidate_id": record_id,
                    "outcome": "not_promoted",
                    "reactivation_conditions": [
                        "Reconsider when authoritative workflow evidence changes."
                    ],
                },
                "decisions": {
                    "schema_version": 2,
                    "candidate_id": record_id,
                    "outcome": "not_promoted",
                    "source_refs": ["benchmark-source"],
                },
            }
            for group, payload in payloads.items():
                (root / group / f"{record_id}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
        write_seconds = perf_counter() - write_started

        files = sorted(root.glob("*/*.json"))
        byte_count = sum(path.stat().st_size for path in files)
        read_started = perf_counter()
        parsed = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in files
        ]
        read_seconds = perf_counter() - read_started
        return {
            "schema_version": 1,
            "records": records,
            "files": len(files),
            "bytes": byte_count,
            "parsed_files": len(parsed),
            "write_seconds": round(write_seconds, 6),
            "read_seconds": round(read_seconds, 6),
        }


def benchmark_sqlite_runtime(records: int) -> dict[str, Any]:
    _positive_integer(records, "benchmark records")
    with tempfile.TemporaryDirectory(prefix="skill-harvester-sqlite-") as directory:
        path = Path(directory) / "runtime.sqlite3"
        connection = sqlite3.connect(path)
        try:
            connection.execute(
                "CREATE TABLE discoveries (id TEXT PRIMARY KEY, record_json TEXT NOT NULL)"
            )
            write_started = perf_counter()
            with connection:
                connection.executemany(
                    "INSERT INTO discoveries(id, record_json) VALUES(?, ?)",
                    [
                        (
                            f"candidate-{index:08d}",
                            json.dumps(
                                {
                                    "schema_version": 1,
                                    "id": f"candidate-{index:08d}",
                                    "source_id": "benchmark-source",
                                    "review_status": "pending",
                                    "evidence_sha256": "a" * 64,
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        )
                        for index in range(records)
                    ],
                )
            write_seconds = perf_counter() - write_started
            read_started = perf_counter()
            parsed = list(connection.execute("SELECT record_json FROM discoveries ORDER BY id"))
            read_seconds = perf_counter() - read_started
        finally:
            connection.close()
        return {
            "schema_version": 1,
            "records": records,
            "bytes": path.stat().st_size,
            "parsed_records": len(parsed),
            "write_seconds": round(write_seconds, 6),
            "read_seconds": round(read_seconds, 6),
        }
