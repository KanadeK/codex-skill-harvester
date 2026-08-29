from __future__ import annotations

import os
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from .io import canonical_json_bytes, load_json, sha256_bytes


RUNTIME_DB = Path("state") / "harvest.sqlite3"
SCHEMA_VERSION = 2

QUEUE_PRIORITY = {
    "urgent-impact": 0,
    "official-gap": 1,
    "reactivation": 2,
    "novel-discovery": 3,
    "aged-backlog": 4,
}
TRUST_PRIORITY = {"official": 0, "representative": 1, "discovery": 2}


class RuntimeStoreError(ValueError):
    pass


def _json_text(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def _json_value(value: str) -> Any:
    import json

    return json.loads(value)


def _observation_l0_key(observation: dict[str, Any]) -> str:
    source_item_id = observation.get(
        "source_item_id", observation.get("canonical_url")
    )
    if not isinstance(source_item_id, str) or not source_item_id:
        raise RuntimeStoreError("runtime observation needs a source item identity")
    return "\u001f".join(
        (
            str(observation["source_id"]),
            source_item_id,
            str(observation["source_revision"]),
        )
    )


def queue_for_candidate(candidate: dict[str, Any]) -> str:
    if candidate.get("published_impact"):
        return "urgent-impact"
    if candidate.get("trust") == "official" and candidate.get(
        "operational_authority"
    ):
        return "official-gap"
    if candidate.get("reactivated"):
        return "reactivation"
    if candidate.get("aged_backlog"):
        return "aged-backlog"
    return "novel-discovery"


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

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
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE source_states (
                    source_id TEXT PRIMARY KEY,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE observations (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_group TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    source_revision TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    trust TEXT NOT NULL,
                    authority TEXT NOT NULL,
                    l0_key TEXT NOT NULL UNIQUE,
                    l1_evidence_sha256 TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX observations_source_revision
                    ON observations (source_id, source_revision);
                CREATE INDEX observations_normalization
                    ON observations (source_id, observed_at, id);
                CREATE TABLE candidates (
                    id TEXT PRIMARY KEY,
                    observation_id TEXT NOT NULL UNIQUE REFERENCES observations(id),
                    source_id TEXT NOT NULL,
                    source_group TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    trust TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    queue_name TEXT NOT NULL,
                    queue_rank INTEGER NOT NULL,
                    trust_rank INTEGER NOT NULL,
                    l2_fingerprint_sha256 TEXT NOT NULL,
                    l3_recall_count INTEGER NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX candidates_review_page
                    ON candidates (
                        review_status,
                        queue_rank,
                        trust_rank,
                        observed_at,
                        id
                    );
                CREATE INDEX candidates_source_review_page
                    ON candidates (
                        source_id,
                        review_status,
                        queue_rank,
                        trust_rank,
                        observed_at,
                        id
                    );
                CREATE INDEX candidates_l2_fingerprint
                    ON candidates (l2_fingerprint_sha256);
                CREATE TABLE decisions (
                    candidate_id TEXT PRIMARY KEY REFERENCES candidates(id),
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
        return str(row["value"])

    def source_state(self, source_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM source_states WHERE source_id = ?", (source_id,)
        ).fetchone()
        return {} if row is None else _json_value(row["record_json"])

    def source_state_count(self) -> int:
        self.validate()
        return int(
            self.connection.execute("SELECT COUNT(*) FROM source_states").fetchone()[0]
        )

    def source_states(self) -> Iterator[tuple[str, dict[str, Any]]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT source_id, record_json FROM source_states ORDER BY source_id"
        )
        for row in rows:
            yield str(row["source_id"]), _json_value(row["record_json"])

    def observation(self, observation_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM observations WHERE id = ?", (observation_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown runtime observation: {observation_id}")
        return _json_value(row["record_json"])

    def observations(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM observations ORDER BY observed_at, id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def observation_count(self) -> int:
        self.validate()
        return int(
            self.connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        )

    def unpromoted_observations(
        self, source_ids: set[str]
    ) -> Iterator[dict[str, Any]]:
        self.validate()
        placeholders = ",".join("?" for _ in source_ids)
        rows = self.connection.execute(
            "SELECT observations.record_json FROM observations "
            "LEFT JOIN candidates ON candidates.observation_id = observations.id "
            f"WHERE candidates.id IS NULL AND observations.source_id IN ({placeholders}) "
            "ORDER BY observations.observed_at, observations.id",
            tuple(sorted(source_ids)),
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def candidate(self, candidate_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown runtime candidate: {candidate_id}")
        return _json_value(row["record_json"])

    def candidates(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM candidates ORDER BY observed_at, id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def candidate_count(self) -> int:
        self.validate()
        return int(
            self.connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        )

    def l2_matches(self, fingerprint: dict[str, Any]) -> list[str]:
        self.validate()
        fingerprint_hash = sha256_bytes(canonical_json_bytes(fingerprint))
        rows = self.connection.execute(
            "SELECT id FROM candidates WHERE l2_fingerprint_sha256 = ? ORDER BY id",
            (fingerprint_hash,),
        )
        return [str(row["id"]) for row in rows]

    def decision_count(self) -> int:
        self.validate()
        return int(
            self.connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        )

    def decisions(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM decisions ORDER BY candidate_id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def candidate_status_counts(self) -> dict[str, int]:
        self.validate()
        rows = self.connection.execute(
            "SELECT review_status, COUNT(*) AS count FROM candidates GROUP BY review_status"
        )
        return {str(row["review_status"]): int(row["count"]) for row in rows}

    def pending_by_source(self) -> dict[str, int]:
        self.validate()
        rows = self.connection.execute(
            "SELECT source_id, COUNT(*) AS count FROM candidates "
            "WHERE review_status = 'pending' GROUP BY source_id ORDER BY source_id"
        )
        return {str(row["source_id"]): int(row["count"]) for row in rows}

    def decision_outcome_counts(self) -> dict[str, int]:
        self.validate()
        rows = self.connection.execute(
            "SELECT outcome, COUNT(*) AS count FROM decisions GROUP BY outcome ORDER BY outcome"
        )
        counts: Counter[str] = Counter()
        for row in rows:
            outcome = "not_promoted" if row["outcome"] == "discard" else str(row["outcome"])
            counts[outcome] += int(row["count"])
        return dict(sorted(counts.items()))

    def insert_observation(self, observation: dict[str, Any]) -> bool:
        result = self.connection.execute(
            "INSERT OR IGNORE INTO observations("
            "id, source_id, source_group, topic_id, source_revision, observed_at, trust, "
            "authority, l0_key, l1_evidence_sha256, record_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation["id"],
                observation["source_id"],
                observation["source_group"],
                observation["topic_id"],
                observation["source_revision"],
                observation["observed_at"],
                observation["trust"],
                observation["authority"],
                _observation_l0_key(observation),
                observation["evidence_sha256"],
                _json_text(observation),
            ),
        )
        return result.rowcount == 1

    def insert_candidate(self, candidate: dict[str, Any]) -> bool:
        queue_name = queue_for_candidate(candidate)
        trust = str(candidate["trust"])
        if queue_name not in QUEUE_PRIORITY or trust not in TRUST_PRIORITY:
            raise RuntimeStoreError("runtime candidate has invalid queue metadata")
        value = dict(candidate)
        value["queue"] = queue_name
        fingerprint_hash = sha256_bytes(canonical_json_bytes(value["fingerprint"]))
        result = self.connection.execute(
            "INSERT OR IGNORE INTO candidates("
            "id, observation_id, source_id, source_group, topic_id, observed_at, trust, "
            "review_status, queue_name, queue_rank, trust_rank, l2_fingerprint_sha256, "
            "l3_recall_count, record_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                value["id"],
                value["observation_id"],
                value["source_id"],
                value["source_group"],
                value["topic_id"],
                value["observed_at"],
                trust,
                value["review_status"],
                queue_name,
                QUEUE_PRIORITY[queue_name],
                TRUST_PRIORITY[trust],
                fingerprint_hash,
                len(value["l3_recall"]),
                _json_text(value),
            ),
        )
        return result.rowcount == 1

    def commit_scan(
        self,
        *,
        now: str,
        source_states: dict[str, dict[str, Any]],
        observations: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> dict[str, int]:
        self.validate()
        inserted_observations = 0
        inserted_candidates = 0
        inserted_l3_recalls = 0
        with self.connection:
            for source_id, state in source_states.items():
                self.connection.execute(
                    "INSERT INTO source_states(source_id, record_json) VALUES(?, ?) "
                    "ON CONFLICT(source_id) DO UPDATE SET record_json = excluded.record_json",
                    (source_id, _json_text(state)),
                )
            for observation in observations:
                if self.insert_observation(observation):
                    inserted_observations += 1
            for candidate in candidates:
                if self.insert_candidate(candidate):
                    inserted_candidates += 1
                    inserted_l3_recalls += len(candidate["l3_recall"])
            self._set_meta("last_successful_run", now)
        return {
            "observations_inserted": inserted_observations,
            "observation_duplicates": len(observations) - inserted_observations,
            "normalized_candidates": inserted_candidates,
            "candidate_duplicates": len(candidates) - inserted_candidates,
            "l3_recalls": inserted_l3_recalls,
        }

    def review_page(
        self, *, source_id: str | None, limit: int, after: str | None
    ) -> dict[str, Any]:
        self.validate()
        source_clause = " AND source_id = ?" if source_id is not None else ""
        source_parameters: tuple[Any, ...] = (source_id,) if source_id is not None else ()
        pending = int(
            self.connection.execute(
                "SELECT COUNT(*) FROM candidates WHERE review_status = 'pending'"
                + source_clause,
                source_parameters,
            ).fetchone()[0]
        )
        by_source_rows = self.connection.execute(
            "SELECT source_id, COUNT(*) AS count FROM candidates "
            "WHERE review_status = 'pending'"
            + source_clause
            + " GROUP BY source_id ORDER BY source_id",
            source_parameters,
        )
        by_source = {
            str(row["source_id"]): int(row["count"]) for row in by_source_rows
        }

        cursor_clause = ""
        cursor_parameters: tuple[Any, ...] = ()
        if after is not None:
            cursor = self.connection.execute(
                "SELECT source_id, review_status, queue_rank, trust_rank, observed_at, id "
                "FROM candidates WHERE id = ?",
                (after,),
            ).fetchone()
            if cursor is None or cursor["review_status"] != "pending":
                raise RuntimeStoreError(f"unknown review cursor: {after}")
            if source_id is not None and cursor["source_id"] != source_id:
                raise RuntimeStoreError("review cursor is outside the selected source")
            cursor_clause = (
                " AND (queue_rank, trust_rank, observed_at, id) > (?, ?, ?, ?)"
            )
            cursor_parameters = (
                cursor["queue_rank"],
                cursor["trust_rank"],
                cursor["observed_at"],
                cursor["id"],
            )

        rows = list(
            self.connection.execute(
                "SELECT record_json FROM candidates WHERE review_status = 'pending'"
                + source_clause
                + cursor_clause
                + " ORDER BY queue_rank, trust_rank, observed_at, id LIMIT ?",
                source_parameters + cursor_parameters + (limit + 1,),
            )
        )
        has_more = len(rows) > limit
        records = [_json_value(row["record_json"]) for row in rows[:limit]]
        return {
            "pending": pending,
            "by_source": by_source,
            "records": records,
            "next_cursor": records[-1]["id"] if has_more else None,
        }

    def record_run(self, report: dict[str, Any]) -> None:
        self.validate()
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs(run_id, status, report_json) VALUES(?, ?, ?)",
                (report["run_id"], report["status"], _json_text(report)),
            )

    def record_failed_run(self, report: dict[str, Any]) -> None:
        self.record_run(report)

    def record_decision(self, candidate_id: str, record: dict[str, Any]) -> None:
        self.validate()
        with self.connection:
            row = self.connection.execute(
                "SELECT record_json FROM candidates WHERE id = ?", (candidate_id,)
            ).fetchone()
            if row is None:
                raise RuntimeStoreError(f"unknown runtime candidate: {candidate_id}")
            self.connection.execute(
                "INSERT INTO decisions(candidate_id, outcome, record_json) VALUES(?, ?, ?) "
                "ON CONFLICT(candidate_id) DO UPDATE SET outcome = excluded.outcome, "
                "record_json = excluded.record_json",
                (candidate_id, str(record["outcome"]), _json_text(record)),
            )
            candidate = _json_value(row["record_json"])
            candidate["review_status"] = "applied"
            candidate["decision_outcome"] = record["outcome"]
            candidate["decision_record"] = f"sqlite:decisions/{candidate_id}"
            self.connection.execute(
                "UPDATE candidates SET review_status = ?, record_json = ? WHERE id = ?",
                ("applied", _json_text(candidate), candidate_id),
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
        discoveries_by_id = {record["id"]: record for record in discoveries}
        decisions_by_id = {record["candidate_id"]: record for record in decisions}
        with self.connection:
            for source_id, source_state in state["sources"].items():
                self.connection.execute(
                    "INSERT INTO source_states(source_id, record_json) VALUES(?, ?)",
                    (source_id, _json_text(source_state)),
                )
            for discovery in discoveries:
                observation = {
                    **discovery,
                    "schema_version": 2,
                    "source_group": "legacy-import",
                    "topic_id": "legacy.reviewed",
                }
                for field in (
                    "review_status",
                    "decision_outcome",
                    "decision_record",
                ):
                    observation.pop(field, None)
                if not self.insert_observation(observation):
                    raise RuntimeStoreError(
                        f"legacy import contains duplicate observation: {observation['id']}"
                    )
            for candidate_id, record in decisions_by_id.items():
                discovery = discoveries_by_id.get(candidate_id)
                if discovery is None:
                    raise RuntimeStoreError(
                        f"legacy decision references an unknown discovery: {candidate_id}"
                    )
                candidate = {
                    "schema_version": 2,
                    "id": candidate_id,
                    "observation_id": candidate_id,
                    "source_id": discovery["source_id"],
                    "source_group": "legacy-import",
                    "topic_id": "legacy.reviewed",
                    "observed_at": discovery["observed_at"],
                    "title": discovery["title"],
                    "canonical_url": discovery["canonical_url"],
                    "evidence_sha256": discovery["evidence_sha256"],
                    "trust": discovery["trust"],
                    "license": discovery["license"],
                    "fingerprint": record["fingerprint"],
                    "l3_recall": [],
                    "review_status": "pending",
                    "aged_backlog": True,
                }
                if not self.insert_candidate(candidate):
                    raise RuntimeStoreError(
                        f"legacy import contains duplicate candidate: {candidate_id}"
                    )
                self.record_decision(candidate_id, record)
            self._set_meta(
                "last_successful_run", str(state.get("last_successful_run") or "null")
            )


def runtime_store_path(root: Path) -> Path:
    return root / RUNTIME_DB


def open_runtime_store(root: Path) -> RuntimeStore:
    path = runtime_store_path(root)
    if not path.is_file():
        raise RuntimeStoreError(
            f"runtime store is missing: {RUNTIME_DB.as_posix()}"
        )
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


def _legacy_records(
    root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    state = load_json(root / "state" / "harvest-state.json")
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise RuntimeStoreError("legacy harvest state is invalid")
    discoveries = [
        load_json(path)
        for path in sorted((root / "candidates" / "inbox").glob("*.json"))
    ]
    decisions = [
        load_json(path)
        for path in sorted((root / "decisions" / "records").glob("*.json"))
    ]
    if any(not isinstance(record, dict) for record in discoveries + decisions):
        raise RuntimeStoreError("legacy runtime record is invalid")
    return state, discoveries, decisions


def _legacy_digest(root: Path) -> str:
    paths = [root / "state" / "harvest-state.json"]
    paths.extend(sorted((root / "candidates" / "inbox").glob("*.json")))
    paths.extend(sorted((root / "decisions" / "records").glob("*.json")))
    payload = b"".join(
        path.relative_to(root).as_posix().encode("utf-8")
        + b"\0"
        + path.read_bytes()
        for path in paths
    )
    return sha256_bytes(payload)


def import_legacy_runtime(root: Path) -> dict[str, Any]:
    destination = runtime_store_path(root)
    if destination.exists():
        raise RuntimeStoreError(
            "runtime store already exists; legacy import is one-time only"
        )
    state, discoveries, decisions = _legacy_records(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".harvest-import-", suffix=".sqlite3", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with RuntimeStore(temporary) as store:
            store.initialize()
            store.import_records(
                state=state, discoveries=discoveries, decisions=decisions
            )
            if store.source_state_count() != len(state["sources"]):
                raise RuntimeStoreError("legacy source-state count did not migrate")
            if store.observation_count() != len(discoveries):
                raise RuntimeStoreError("legacy observation count did not migrate")
            if store.candidate_count() != len(decisions):
                raise RuntimeStoreError("legacy candidate count did not migrate")
            if store.decision_count() != len(decisions):
                raise RuntimeStoreError("legacy decision count did not migrate")
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "schema_version": 2,
        "backend": "sqlite-v2",
        "source_states": len(state["sources"]),
        "observations": len(discoveries),
        "candidates": len(decisions),
        "decisions": len(decisions),
        "legacy_sha256": _legacy_digest(root),
    }
