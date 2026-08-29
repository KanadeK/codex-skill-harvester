from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterator

from .io import canonical_json_bytes, load_json, sha256_bytes


RUNTIME_DB = Path("state") / "harvest.sqlite3"
SCHEMA_VERSION = 1


class RuntimeStoreError(ValueError):
    pass


def _json_text(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def _json_value(value: str) -> Any:
    import json

    return json.loads(value)


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row

    def __enter__(self) -> RuntimeStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE source_states (
                    source_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE discoveries (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    trust TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    queue_name TEXT NOT NULL,
                    l0_key TEXT NOT NULL UNIQUE,
                    l1_evidence_sha256 TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX discoveries_queue_order
                    ON discoveries (review_status, queue_name, observed_at, id);
                CREATE INDEX discoveries_source_revision
                    ON discoveries (source_id, source_revision);
                CREATE TABLE decisions (
                    candidate_id TEXT PRIMARY KEY REFERENCES discoveries(id),
                    outcome TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    report_json TEXT NOT NULL
                );
                """
            )
            self._set_meta("schema_version", str(SCHEMA_VERSION))
            self._set_meta("last_successful_run", "null")

    def validate(self) -> None:
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = ?", ("schema_version",)
        ).fetchone()
        if row is None or row["value"] != str(SCHEMA_VERSION):
            raise RuntimeStoreError("runtime store has an unsupported schema version")

    def _set_meta(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def last_successful_run(self) -> str | None:
        self.validate()
        row = self.connection.execute(
            "SELECT value FROM metadata WHERE key = ?", ("last_successful_run",)
        ).fetchone()
        if row is None or row["value"] == "null":
            return None
        return row["value"]

    def source_state(self, source_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM source_states WHERE source_id = ?", (source_id,)
        ).fetchone()
        return {} if row is None else _json_value(row["record_json"])

    def source_state_count(self) -> int:
        self.validate()
        return int(self.connection.execute("SELECT COUNT(*) FROM source_states").fetchone()[0])

    def source_states(self) -> Iterator[tuple[str, dict[str, Any]]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT source_id, record_json FROM source_states ORDER BY source_id"
        )
        for row in rows:
            yield str(row["source_id"]), _json_value(row["record_json"])

    def discovery(self, candidate_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM discoveries WHERE id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown runtime candidate: {candidate_id}")
        return _json_value(row["record_json"])

    def discoveries(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM discoveries ORDER BY observed_at, id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def discovery_count(self) -> int:
        self.validate()
        return int(self.connection.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0])

    def decision_count(self) -> int:
        self.validate()
        return int(self.connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0])

    def decisions(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM decisions ORDER BY candidate_id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def queue_entries(self) -> Iterator[tuple[dict[str, Any], str]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json, queue_name FROM discoveries "
            "WHERE review_status = ? ORDER BY observed_at, id",
            ("pending",),
        )
        for row in rows:
            yield _json_value(row["record_json"]), str(row["queue_name"])

    def insert_discovery(self, discovery: dict[str, Any], *, queue_name: str) -> bool:
        source_item_id = discovery.get("source_item_id", discovery.get("canonical_url"))
        if not isinstance(source_item_id, str) or not source_item_id:
            raise RuntimeStoreError("runtime discovery needs a source item identity")
        l0_key = "\u001f".join(
            (str(discovery["source_id"]), source_item_id, str(discovery["source_revision"]))
        )
        result = self.connection.execute(
            "INSERT OR IGNORE INTO discoveries("
            "id, source_id, source_revision, observed_at, trust, review_status, queue_name, "
            "l0_key, l1_evidence_sha256, record_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                discovery["id"],
                discovery["source_id"],
                discovery["source_revision"],
                discovery["observed_at"],
                discovery["trust"],
                discovery["review_status"],
                queue_name,
                l0_key,
                discovery["evidence_sha256"],
                _json_text(discovery),
            ),
        )
        return result.rowcount == 1

    def commit_scan(
        self,
        *,
        now: str,
        source_states: dict[str, dict[str, Any]],
        discoveries: list[dict[str, Any]],
        queue_names: dict[str, str],
    ) -> tuple[int, int]:
        self.validate()
        inserted = 0
        with self.connection:
            for source_id, state in source_states.items():
                self.connection.execute(
                    "INSERT INTO source_states(source_id, record_json) VALUES(?, ?) "
                    "ON CONFLICT(source_id) DO UPDATE SET record_json = excluded.record_json",
                    (source_id, _json_text(state)),
                )
            for discovery in discoveries:
                if self.insert_discovery(discovery, queue_name=queue_names[discovery["id"]]):
                    inserted += 1
            self._set_meta("last_successful_run", now)
        return inserted, len(discoveries) - inserted

    def record_run(self, report: dict[str, Any]) -> None:
        self.validate()
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs(run_id, status, report_json) VALUES(?, ?, ?)",
                (report["run_id"], report["status"], _json_text(report)),
            )

    def record_failed_run(self, report: dict[str, Any]) -> None:
        self.validate()
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs(run_id, status, report_json) VALUES(?, ?, ?)",
                (report["run_id"], report["status"], _json_text(report)),
            )

    def record_decision(self, candidate_id: str, record: dict[str, Any]) -> None:
        self.validate()
        with self.connection:
            self.connection.execute(
                "INSERT INTO decisions(candidate_id, outcome, record_json) VALUES(?, ?, ?) "
                "ON CONFLICT(candidate_id) DO UPDATE SET outcome = excluded.outcome, "
                "record_json = excluded.record_json",
                (candidate_id, str(record["outcome"]), _json_text(record)),
            )
            row = self.connection.execute(
                "SELECT record_json FROM discoveries WHERE id = ?", (candidate_id,)
            ).fetchone()
            if row is None:
                raise RuntimeStoreError(f"unknown runtime candidate: {candidate_id}")
            discovery = _json_value(row["record_json"])
            discovery["review_status"] = "applied"
            discovery["decision_outcome"] = record["outcome"]
            discovery["decision_record"] = f"sqlite:decisions/{candidate_id}"
            self.connection.execute(
                "UPDATE discoveries SET review_status = ?, record_json = ? WHERE id = ?",
                ("applied", _json_text(discovery), candidate_id),
            )

    def import_records(
        self,
        *,
        state: dict[str, Any],
        discoveries: list[dict[str, Any]],
        decisions: list[dict[str, Any]],
    ) -> None:
        if not isinstance(state.get("sources"), dict):
            raise RuntimeStoreError("legacy harvest state is invalid")
        with self.connection:
            for source_id, source_state in state["sources"].items():
                self.connection.execute(
                    "INSERT INTO source_states(source_id, record_json) VALUES(?, ?)",
                    (source_id, _json_text(source_state)),
                )
            for discovery in discoveries:
                queue_name = queue_for_discovery(discovery)
                if not self.insert_discovery(discovery, queue_name=queue_name):
                    raise RuntimeStoreError(f"legacy import contains duplicate discovery: {discovery['id']}")
            for record in decisions:
                candidate_id = record.get("candidate_id")
                if not isinstance(candidate_id, str):
                    raise RuntimeStoreError("legacy decision has no candidate_id")
                self.connection.execute(
                    "INSERT INTO decisions(candidate_id, outcome, record_json) VALUES(?, ?, ?)",
                    (candidate_id, str(record.get("outcome")), _json_text(record)),
                )
                row = self.connection.execute(
                    "SELECT record_json FROM discoveries WHERE id = ?", (candidate_id,)
                ).fetchone()
                if row is None:
                    raise RuntimeStoreError(
                        f"legacy decision references an unknown discovery: {candidate_id}"
                    )
                discovery = _json_value(row["record_json"])
                discovery["review_status"] = "applied"
                discovery["decision_outcome"] = record.get("outcome")
                discovery["decision_record"] = f"sqlite:decisions/{candidate_id}"
                self.connection.execute(
                    "UPDATE discoveries SET review_status = ?, record_json = ? WHERE id = ?",
                    ("applied", _json_text(discovery), candidate_id),
                )
            self._set_meta("last_successful_run", str(state.get("last_successful_run") or "null"))


def runtime_store_path(root: Path) -> Path:
    return root / RUNTIME_DB


def open_runtime_store(root: Path) -> RuntimeStore:
    path = runtime_store_path(root)
    if not path.is_file():
        raise RuntimeStoreError(f"runtime store is missing: {RUNTIME_DB.as_posix()}")
    store = RuntimeStore(path)
    try:
        store.validate()
    except BaseException:
        store.close()
        raise
    return store


def create_empty_runtime(root: Path) -> None:
    destination = runtime_store_path(root)
    if destination.exists():
        raise RuntimeStoreError("runtime store already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with RuntimeStore(destination) as store:
        store.initialize()


def queue_for_discovery(discovery: dict[str, Any]) -> str:
    if discovery.get("review_status") == "reactivated":
        return "reactivation"
    if discovery.get("published_impact"):
        return "urgent-impact"
    if discovery.get("trust") == "official":
        return "official-gap"
    if discovery.get("aged_backlog"):
        return "aged-backlog"
    if discovery.get("observed_at"):
        return "novel-discovery"
    return "aged-backlog"


def _legacy_records(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    state = load_json(root / "state" / "harvest-state.json")
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise RuntimeStoreError("legacy harvest state is invalid")
    discoveries = [
        load_json(path) for path in sorted((root / "candidates" / "inbox").glob("*.json"))
    ]
    decisions = [
        load_json(path) for path in sorted((root / "decisions" / "records").glob("*.json"))
    ]
    if any(not isinstance(record, dict) for record in discoveries + decisions):
        raise RuntimeStoreError("legacy runtime record is invalid")
    return state, discoveries, decisions


def _legacy_digest(root: Path) -> str:
    paths = [root / "state" / "harvest-state.json"]
    paths.extend(sorted((root / "candidates" / "inbox").glob("*.json")))
    paths.extend(sorted((root / "decisions" / "records").glob("*.json")))
    payload = b"".join(path.relative_to(root).as_posix().encode("utf-8") + b"\0" + path.read_bytes() for path in paths)
    return sha256_bytes(payload)


def import_legacy_runtime(root: Path) -> dict[str, Any]:
    destination = runtime_store_path(root)
    if destination.exists():
        raise RuntimeStoreError("runtime store already exists; legacy import is one-time only")
    state, discoveries, decisions = _legacy_records(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".harvest-import-", suffix=".sqlite3", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with RuntimeStore(temporary) as store:
            store.initialize()
            store.import_records(state=state, discoveries=discoveries, decisions=decisions)
            if store.source_state_count() != len(state["sources"]):
                raise RuntimeStoreError("legacy source-state count did not migrate")
            if store.discovery_count() != len(discoveries):
                raise RuntimeStoreError("legacy discovery count did not migrate")
            if store.decision_count() != len(decisions):
                raise RuntimeStoreError("legacy decision count did not migrate")
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "schema_version": 1,
        "backend": "sqlite-v1",
        "source_states": len(state["sources"]),
        "discoveries": len(discoveries),
        "decisions": len(decisions),
        "legacy_sha256": _legacy_digest(root),
    }
