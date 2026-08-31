from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from .io import canonical_json_bytes, load_json, sha256_bytes


RUNTIME_DB = Path("state") / "harvest.sqlite3"
SCHEMA_VERSION = 4

QUEUE_PRIORITY = {
    "urgent-impact": 0,
    "official-gap": 1,
    "reactivation": 2,
    "novel-discovery": 3,
    "aged-backlog": 4,
}
TRUST_PRIORITY = {"official": 0, "representative": 1, "discovery": 2}
TIER_PRIORITY = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}


class RuntimeStoreError(ValueError):
    pass


def discovery_hit_id(hit: dict[str, Any]) -> str:
    seed = (
        {
            "route": hit["route"],
            "url": hit["url"].split("#", 1)[0],
        }
        if hit["route"] == "web"
        else {
            "route": hit["route"],
            "repository": hit["repository"].casefold(),
            "path": hit.get("path"),
        }
    )
    return sha256_bytes(b"discovery-hit\0" + canonical_json_bytes(seed))[:24]


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
                    tier TEXT NOT NULL,
                    tier_rank INTEGER NOT NULL,
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
                    ON observations (tier_rank, observed_at, id);
                CREATE TABLE semantic_batches (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX semantic_batches_pending
                    ON semantic_batches (status, created_at, id);
                CREATE TABLE evidence_packs (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT REFERENCES semantic_batches(id),
                    outcome TEXT NOT NULL,
                    reviewed_at TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE semantic_batch_items (
                    batch_id TEXT NOT NULL REFERENCES semantic_batches(id),
                    observation_id TEXT NOT NULL REFERENCES observations(id),
                    status TEXT NOT NULL,
                    evidence_pack_id TEXT REFERENCES evidence_packs(id),
                    PRIMARY KEY (batch_id, observation_id)
                );
                CREATE UNIQUE INDEX semantic_reviewed_observation
                    ON semantic_batch_items (observation_id)
                    WHERE status = 'reviewed';
                CREATE TABLE candidates (
                    id TEXT PRIMARY KEY,
                    evidence_pack_id TEXT NOT NULL UNIQUE REFERENCES evidence_packs(id),
                    observation_id TEXT NOT NULL REFERENCES observations(id),
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
                CREATE TABLE source_utility (
                    source_id TEXT PRIMARY KEY,
                    source_requests INTEGER NOT NULL,
                    successes INTEGER NOT NULL,
                    failures INTEGER NOT NULL,
                    downloaded_bytes INTEGER NOT NULL,
                    observations INTEGER NOT NULL,
                    candidates INTEGER NOT NULL
                );
                CREATE TABLE query_batches (
                    id TEXT PRIMARY KEY,
                    cycle_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX query_batches_pending
                    ON query_batches (status, created_at, id);
                CREATE INDEX query_batches_cycle
                    ON query_batches (cycle_id, status, created_at, id);
                CREATE TABLE query_batch_items (
                    batch_id TEXT NOT NULL REFERENCES query_batches(id),
                    query_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    PRIMARY KEY (batch_id, query_id)
                );
                CREATE INDEX query_items_status
                    ON query_batch_items (batch_id, status, query_id);
                CREATE TABLE query_states (
                    query_id TEXT PRIMARY KEY,
                    last_completed_cycle TEXT NOT NULL,
                    last_completed_at TEXT NOT NULL,
                    cursor TEXT,
                    result_count INTEGER NOT NULL,
                    selected_endpoint_count INTEGER NOT NULL,
                    record_json TEXT NOT NULL
                );
                CREATE TABLE discovery_hits (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    selected_source_id TEXT,
                    record_json TEXT NOT NULL
                );
                CREATE INDEX discovery_hits_review_page
                    ON discovery_hits (status, first_seen_at, id);
                CREATE TABLE discovery_hit_occurrences (
                    hit_id TEXT NOT NULL REFERENCES discovery_hits(id),
                    cycle_id TEXT NOT NULL,
                    query_id TEXT NOT NULL,
                    source_group TEXT NOT NULL,
                    topic_id TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    PRIMARY KEY (hit_id, cycle_id, query_id)
                );
                CREATE INDEX discovery_hit_occurrences_cycle
                    ON discovery_hit_occurrences (cycle_id, hit_id);
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

    def semantic_batch(self, batch_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM semantic_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown semantic batch: {batch_id}")
        return _json_value(row["record_json"])

    def evidence_pack(self, evidence_pack_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM evidence_packs WHERE id = ?", (evidence_pack_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown evidence pack: {evidence_pack_id}")
        return _json_value(row["record_json"])

    def evidence_packs(self) -> Iterator[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM evidence_packs ORDER BY reviewed_at, id"
        )
        for row in rows:
            yield _json_value(row["record_json"])

    def evidence_packs_for_batch(self, batch_id: str) -> list[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM evidence_packs "
            "WHERE batch_id = ? ORDER BY reviewed_at, id",
            (batch_id,),
        )
        return [_json_value(row["record_json"]) for row in rows]

    def semantic_batch_items(self, batch_id: str) -> list[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT observation_id, status, evidence_pack_id "
            "FROM semantic_batch_items WHERE batch_id = ? ORDER BY observation_id",
            (batch_id,),
        )
        return [dict(row) for row in rows]

    def candidates_for_evidence_packs(
        self, evidence_pack_ids: set[str]
    ) -> list[dict[str, Any]]:
        self.validate()
        if not evidence_pack_ids:
            return []
        placeholders = ",".join("?" for _ in evidence_pack_ids)
        rows = self.connection.execute(
            "SELECT record_json FROM candidates "
            f"WHERE evidence_pack_id IN ({placeholders}) ORDER BY id",
            tuple(sorted(evidence_pack_ids)),
        )
        return [_json_value(row["record_json"]) for row in rows]

    def decisions_for_candidates(
        self, candidate_ids: set[str]
    ) -> list[dict[str, Any]]:
        self.validate()
        if not candidate_ids:
            return []
        placeholders = ",".join("?" for _ in candidate_ids)
        rows = self.connection.execute(
            "SELECT record_json FROM decisions "
            f"WHERE candidate_id IN ({placeholders}) ORDER BY candidate_id",
            tuple(sorted(candidate_ids)),
        )
        return [_json_value(row["record_json"]) for row in rows]

    def create_or_resume_semantic_batch(
        self, *, now: str, limit: int
    ) -> dict[str, Any]:
        self.validate()
        if limit < 1:
            raise RuntimeStoreError("semantic batch limit must be positive")
        active = self.connection.execute(
            "SELECT id FROM semantic_batches WHERE status = 'pending' "
            "ORDER BY created_at, id LIMIT 1"
        ).fetchone()
        if active is not None:
            batch_id = str(active["id"])
            records = self.semantic_batch_pending_observations(batch_id, limit=limit)
            return {
                "batch_id": batch_id,
                "created": False,
                "observations": records,
            }

        rows = list(
            self.connection.execute(
                "SELECT observations.record_json FROM observations "
                "WHERE tier_rank <= ? "
                "AND NOT EXISTS ("
                "SELECT 1 FROM semantic_batch_items "
                "WHERE semantic_batch_items.observation_id = observations.id"
                ") "
                "AND NOT EXISTS ("
                "SELECT 1 FROM candidates "
                "WHERE candidates.observation_id = observations.id"
                ") "
                "ORDER BY tier_rank, observed_at, id LIMIT ?",
                (TIER_PRIORITY["T2"], limit),
            )
        )
        observations = [_json_value(row["record_json"]) for row in rows]
        if not observations:
            return {"batch_id": None, "created": False, "observations": []}
        batch_id = sha256_bytes(
            canonical_json_bytes(
                {
                    "kind": "semantic-batch",
                    "created_at": now,
                    "observation_ids": [record["id"] for record in observations],
                }
            )
        )[:24]
        record = {
            "schema_version": 1,
            "id": batch_id,
            "status": "pending",
            "created_at": now,
            "completed_at": None,
            "observation_count": len(observations),
        }
        with self.connection:
            self.connection.execute(
                "INSERT INTO semantic_batches(id, status, created_at, completed_at, record_json) "
                "VALUES(?, 'pending', ?, NULL, ?)",
                (batch_id, now, _json_text(record)),
            )
            self.connection.executemany(
                "INSERT INTO semantic_batch_items(batch_id, observation_id, status, evidence_pack_id) "
                "VALUES(?, ?, 'pending', NULL)",
                ((batch_id, observation["id"]) for observation in observations),
            )
        return {"batch_id": batch_id, "created": True, "observations": observations}

    def semantic_batch_pending_observations(
        self, batch_id: str, *, limit: int
    ) -> list[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT observations.record_json FROM semantic_batch_items "
            "JOIN observations ON observations.id = semantic_batch_items.observation_id "
            "WHERE semantic_batch_items.batch_id = ? "
            "AND semantic_batch_items.status = 'pending' "
            "ORDER BY observations.tier_rank, observations.observed_at, observations.id "
            "LIMIT ?",
            (batch_id, limit),
        )
        return [_json_value(row["record_json"]) for row in rows]

    def semantic_batch_pending_count(self, batch_id: str) -> int:
        self.validate()
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM semantic_batch_items "
                "WHERE batch_id = ? AND status = 'pending'",
                (batch_id,),
            ).fetchone()[0]
        )

    def semantic_batch_observation_ids(self, batch_id: str) -> set[str]:
        self.validate()
        rows = self.connection.execute(
            "SELECT observation_id FROM semantic_batch_items WHERE batch_id = ?",
            (batch_id,),
        )
        return {str(row["observation_id"]) for row in rows}

    def create_or_resume_query_batch(
        self,
        *,
        now: str,
        cycle_id: str,
        queries: list[dict[str, Any]],
        limit: int,
    ) -> dict[str, Any]:
        self.validate()
        if limit < 1:
            raise RuntimeStoreError("query batch limit must be positive")
        active = self.connection.execute(
            "SELECT id, cycle_id FROM query_batches WHERE status = 'pending' "
            "ORDER BY created_at, id LIMIT 1"
        ).fetchone()
        if active is not None:
            if active["cycle_id"] != cycle_id:
                raise RuntimeStoreError(
                    "finish the pending query cycle before starting another cycle: "
                    f"{active['cycle_id']}"
                )
            batch_id = str(active["id"])
            return {
                "batch_id": batch_id,
                "cycle_id": cycle_id,
                "created": False,
                "queries": self.query_batch_pending_records(batch_id, limit=limit),
            }
        completed_ids = {
            str(row["query_id"])
            for row in self.connection.execute(
                "SELECT query_batch_items.query_id FROM query_batch_items "
                "JOIN query_batches ON query_batches.id = query_batch_items.batch_id "
                "WHERE query_batches.cycle_id = ? "
                "AND query_batch_items.status = 'completed'",
                (cycle_id,),
            )
        }
        selected_base = [query for query in queries if query["id"] not in completed_ids][
            :limit
        ]
        if not selected_base:
            return {
                "batch_id": None,
                "cycle_id": cycle_id,
                "created": False,
                "queries": [],
            }
        selected_ids = [query["id"] for query in selected_base]
        placeholders = ",".join("?" for _ in selected_ids)
        prior_states = {
            str(row["query_id"]): _json_value(row["record_json"])
            for row in self.connection.execute(
                "SELECT query_id, record_json FROM query_states "
                f"WHERE query_id IN ({placeholders})",
                tuple(selected_ids),
            )
        }
        selected = [
            {
                **query,
                "continuation_cursor": prior_states.get(query["id"], {}).get(
                    "cursor"
                ),
                "previous_completed_at": prior_states.get(query["id"], {}).get(
                    "last_completed_at"
                ),
            }
            for query in selected_base
        ]
        batch_id = sha256_bytes(
            canonical_json_bytes(
                {
                    "kind": "query-batch",
                    "cycle_id": cycle_id,
                    "created_at": now,
                    "query_ids": [query["id"] for query in selected],
                }
            )
        )[:24]
        record = {
            "schema_version": 1,
            "id": batch_id,
            "cycle_id": cycle_id,
            "status": "pending",
            "created_at": now,
            "completed_at": None,
            "query_count": len(selected),
        }
        with self.connection:
            self.connection.execute(
                "INSERT INTO query_batches("
                "id, cycle_id, status, created_at, completed_at, record_json"
                ") VALUES(?, ?, 'pending', ?, NULL, ?)",
                (batch_id, cycle_id, now, _json_text(record)),
            )
            self.connection.executemany(
                "INSERT INTO query_batch_items(batch_id, query_id, status, record_json) "
                "VALUES(?, ?, 'pending', ?)",
                (
                    (batch_id, query["id"], _json_text(query))
                    for query in selected
                ),
            )
        return {
            "batch_id": batch_id,
            "cycle_id": cycle_id,
            "created": True,
            "queries": selected,
        }

    def query_batch(self, batch_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM query_batches WHERE id = ?", (batch_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown query batch: {batch_id}")
        return _json_value(row["record_json"])

    def query_cycle_metrics(self, cycle_id: str) -> dict[str, Any]:
        self.validate()
        key = f"query_cycle_metrics:{cycle_id}"
        persisted = self.connection.execute(
            "SELECT value FROM metadata WHERE key = ?", (key,)
        ).fetchone()
        if persisted is not None:
            metrics = _json_value(persisted["value"])
            metrics["discovery_review"] = self.discovery_review_metrics(cycle_id)
            metrics["selected_source_ids"] = metrics["discovery_review"][
                "selected_source_ids"
            ]
            return metrics

        metrics: dict[str, Any] = {
            "query_attempts": 0,
            "completed_queries": 0,
            "failed_queries": 0,
            "pending_queries": 0,
            "result_count": 0,
            "discovery_hits": 0,
            "selected_source_ids": [],
        }
        rows = self.connection.execute(
            "SELECT query_batch_items.status, query_batch_items.record_json "
            "FROM query_batch_items JOIN query_batches "
            "ON query_batches.id = query_batch_items.batch_id "
            "WHERE query_batches.cycle_id = ?",
            (cycle_id,),
        )
        for row in rows:
            if row["status"] == "pending":
                metrics["pending_queries"] += 1
            attempt = _json_value(row["record_json"]).get("last_attempt")
            if not isinstance(attempt, dict):
                continue
            metrics["query_attempts"] += 1
            if attempt.get("status") == "completed":
                metrics["completed_queries"] += 1
            elif attempt.get("status") == "failed":
                metrics["failed_queries"] += 1
            metrics["result_count"] += int(attempt.get("result_count", 0))
            metrics["discovery_hits"] += len(attempt.get("discovery_hits", []))
        metrics["discovery_review"] = self.discovery_review_metrics(cycle_id)
        metrics["selected_source_ids"] = metrics["discovery_review"][
            "selected_source_ids"
        ]
        return metrics

    def record_discovery_hits(
        self,
        *,
        cycle_id: str,
        query: dict[str, Any],
        observed_at: str,
        hits: list[dict[str, Any]],
    ) -> int:
        inserted = 0
        for hit in hits:
            hit_id = discovery_hit_id(hit)
            existing = self.connection.execute(
                "SELECT record_json FROM discovery_hits WHERE id = ?", (hit_id,)
            ).fetchone()
            if existing is None:
                record = {
                    "schema_version": 1,
                    "id": hit_id,
                    "status": "pending",
                    "first_seen_at": observed_at,
                    "last_seen_at": observed_at,
                    "seen_count": 1,
                    "hit": hit,
                    "review": None,
                }
                self.connection.execute(
                    "INSERT INTO discovery_hits("
                    "id, status, first_seen_at, last_seen_at, reviewed_at, "
                    "selected_source_id, record_json"
                    ") VALUES(?, 'pending', ?, ?, NULL, NULL, ?)",
                    (hit_id, observed_at, observed_at, _json_text(record)),
                )
                inserted += 1
            occurrence = self.connection.execute(
                "INSERT OR IGNORE INTO discovery_hit_occurrences("
                "hit_id, cycle_id, query_id, source_group, topic_id, observed_at"
                ") VALUES(?, ?, ?, ?, ?, ?)",
                (
                    hit_id,
                    cycle_id,
                    query["id"],
                    query["source_group"],
                    query["topic_id"],
                    observed_at,
                ),
            )
            if existing is not None and occurrence.rowcount:
                record = _json_value(existing["record_json"])
                record["last_seen_at"] = observed_at
                record["seen_count"] = int(record["seen_count"]) + 1
                self.connection.execute(
                    "UPDATE discovery_hits SET last_seen_at = ?, record_json = ? "
                    "WHERE id = ?",
                    (observed_at, _json_text(record), hit_id),
                )
        return inserted

    def discovery_hit(self, hit_id: str) -> dict[str, Any]:
        self.validate()
        row = self.connection.execute(
            "SELECT record_json FROM discovery_hits WHERE id = ?", (hit_id,)
        ).fetchone()
        if row is None:
            raise RuntimeStoreError(f"unknown discovery hit: {hit_id}")
        return _json_value(row["record_json"])

    def discovery_review_page(
        self, *, limit: int, after: str | None
    ) -> dict[str, Any]:
        self.validate()
        parameters: list[Any] = []
        cursor_clause = ""
        if after is not None:
            cursor = self.connection.execute(
                "SELECT first_seen_at, id FROM discovery_hits WHERE id = ?",
                (after,),
            ).fetchone()
            if cursor is None:
                raise RuntimeStoreError(f"unknown discovery review cursor: {after}")
            cursor_clause = (
                "AND (first_seen_at > ? OR (first_seen_at = ? AND id > ?)) "
            )
            parameters.extend(
                (cursor["first_seen_at"], cursor["first_seen_at"], cursor["id"])
            )
        parameters.append(limit + 1)
        rows = self.connection.execute(
            "SELECT id, record_json FROM discovery_hits "
            "WHERE status = 'pending' "
            f"{cursor_clause}ORDER BY first_seen_at, id LIMIT ?",
            parameters,
        ).fetchall()
        page_rows = rows[:limit]
        records: list[dict[str, Any]] = []
        for row in page_rows:
            record = _json_value(row["record_json"])
            contexts = self.connection.execute(
                "SELECT cycle_id, query_id, source_group, topic_id, observed_at "
                "FROM discovery_hit_occurrences WHERE hit_id = ? "
                "ORDER BY cycle_id, query_id",
                (row["id"],),
            ).fetchall()
            record["contexts"] = [dict(context) for context in contexts]
            records.append(record)
        return {
            "records": records,
            "next_cursor": page_rows[-1]["id"] if len(rows) > limit else None,
        }

    def discovery_review_metrics(self, cycle_id: str | None = None) -> dict[str, Any]:
        self.validate()
        if cycle_id is None:
            target = "SELECT id FROM discovery_hits"
            parameters: tuple[Any, ...] = ()
            raw_hits = int(
                self.connection.execute(
                    "SELECT COUNT(*) FROM discovery_hit_occurrences"
                ).fetchone()[0]
            )
        else:
            target = (
                "SELECT DISTINCT hit_id AS id FROM discovery_hit_occurrences "
                "WHERE cycle_id = ?"
            )
            parameters = (cycle_id,)
            raw_hits = int(
                self.connection.execute(
                    "SELECT COUNT(*) FROM discovery_hit_occurrences WHERE cycle_id = ?",
                    (cycle_id,),
                ).fetchone()[0]
            )
        rows = self.connection.execute(
            "SELECT discovery_hits.status, COUNT(*) AS count "
            f"FROM discovery_hits JOIN ({target}) AS target "
            "ON target.id = discovery_hits.id GROUP BY discovery_hits.status",
            parameters,
        ).fetchall()
        counts = {str(row["status"]): int(row["count"]) for row in rows}
        unique_hits = sum(counts.values())
        reviewed = unique_hits - counts.get("pending", 0)
        selected_rows = self.connection.execute(
            "SELECT DISTINCT discovery_hits.selected_source_id "
            f"FROM discovery_hits JOIN ({target}) AS target "
            "ON target.id = discovery_hits.id "
            "WHERE discovery_hits.status = 'selected_endpoint' "
            "ORDER BY discovery_hits.selected_source_id",
            parameters,
        ).fetchall()
        selected_source_ids = [
            str(row["selected_source_id"]) for row in selected_rows
        ]
        return {
            "raw_hits": raw_hits,
            "unique_hits": unique_hits,
            "pending": counts.get("pending", 0),
            "selected_endpoint": counts.get("selected_endpoint", 0),
            "duplicate": counts.get("duplicate", 0),
            "not_selected": counts.get("not_selected", 0),
            "reviewed": reviewed,
            "conversion_rate": (
                round(counts.get("selected_endpoint", 0) / reviewed, 6)
                if reviewed
                else 0.0
            ),
            "selected_source_ids": selected_source_ids,
        }

    def apply_discovery_reviews(
        self, reviews: list[dict[str, Any]]
    ) -> dict[str, int]:
        self.validate()
        applied = 0
        no_op = 0
        with self.connection:
            for review in reviews:
                row = self.connection.execute(
                    "SELECT status, record_json FROM discovery_hits WHERE id = ?",
                    (review["hit_id"],),
                ).fetchone()
                if row is None:
                    raise RuntimeStoreError(
                        f"unknown discovery hit: {review['hit_id']}"
                    )
                record = _json_value(row["record_json"])
                if row["status"] != "pending":
                    if record.get("review") == review:
                        no_op += 1
                        continue
                    raise RuntimeStoreError(
                        f"discovery hit already reviewed: {review['hit_id']}"
                    )
                record["status"] = review["outcome"]
                record["review"] = review
                selected_source_id = (
                    review["selected_endpoint"]["source_id"]
                    if review["outcome"] == "selected_endpoint"
                    else None
                )
                self.connection.execute(
                    "UPDATE discovery_hits SET status = ?, reviewed_at = ?, "
                    "selected_source_id = ?, record_json = ? WHERE id = ?",
                    (
                        review["outcome"],
                        review["reviewed_at"],
                        selected_source_id,
                        _json_text(record),
                        review["hit_id"],
                    ),
                )
                applied += 1
        return {"applied": applied, "no_op": no_op}

    def reopen_failed_discovery_selection(
        self, *, hit_id: str, reopened_at: str, reason: str
    ) -> dict[str, Any]:
        self.validate()
        with self.connection:
            row = self.connection.execute(
                "SELECT status, selected_source_id, record_json "
                "FROM discovery_hits WHERE id = ?",
                (hit_id,),
            ).fetchone()
            if row is None or row["status"] != "selected_endpoint":
                raise RuntimeStoreError(
                    "only a selected discovery hit can be reopened"
                )
            source_id = str(row["selected_source_id"])
            if self.source_state(source_id):
                raise RuntimeStoreError(
                    "a successfully scanned selected source cannot be reopened"
                )
            record = _json_value(row["record_json"])
            history = list(record.get("review_history", []))
            history.append(record["review"])
            record.update(
                {
                    "status": "pending",
                    "review": None,
                    "review_history": history,
                    "last_reopened_at": reopened_at,
                    "last_reopen_reason": reason,
                }
            )
            self.connection.execute(
                "UPDATE discovery_hits SET status = 'pending', reviewed_at = NULL, "
                "selected_source_id = NULL, record_json = ? WHERE id = ?",
                (_json_text(record), hit_id),
            )
        return {"hit_id": hit_id, "source_id": source_id}

    def discovery_hit_cycles(self, hit_ids: set[str]) -> list[str]:
        self.validate()
        if not hit_ids:
            return []
        placeholders = ",".join("?" for _ in hit_ids)
        rows = self.connection.execute(
            "SELECT DISTINCT cycle_id FROM discovery_hit_occurrences "
            f"WHERE hit_id IN ({placeholders}) ORDER BY cycle_id",
            tuple(sorted(hit_ids)),
        )
        return [str(row["cycle_id"]) for row in rows]

    def query_batch_items(self, batch_id: str) -> list[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT query_id, status, record_json FROM query_batch_items "
            "WHERE batch_id = ? ORDER BY query_id",
            (batch_id,),
        )
        return [
            {
                "query_id": str(row["query_id"]),
                "status": str(row["status"]),
                "record": _json_value(row["record_json"]),
            }
            for row in rows
        ]

    def query_batch_pending_records(
        self, batch_id: str, *, limit: int
    ) -> list[dict[str, Any]]:
        self.validate()
        rows = self.connection.execute(
            "SELECT record_json FROM query_batch_items "
            "WHERE batch_id = ? AND status = 'pending' ORDER BY query_id LIMIT ?",
            (batch_id, limit),
        )
        return [_json_value(row["record_json"]) for row in rows]

    def commit_query_results(
        self,
        *,
        batch_id: str,
        executed_at: str,
        results: list[dict[str, Any]],
    ) -> dict[str, int | str]:
        self.validate()
        with self.connection:
            batch = self.connection.execute(
                "SELECT cycle_id, status, record_json FROM query_batches WHERE id = ?",
                (batch_id,),
            ).fetchone()
            if batch is None or batch["status"] != "pending":
                raise RuntimeStoreError(f"query batch is not pending: {batch_id}")
            cycle_id = str(batch["cycle_id"])
            metrics = self.query_cycle_metrics(cycle_id)
            for result in results:
                item = self.connection.execute(
                    "SELECT record_json FROM query_batch_items "
                    "WHERE batch_id = ? AND query_id = ? AND status = 'pending'",
                    (batch_id, result["query_id"]),
                ).fetchone()
                if item is None:
                    raise RuntimeStoreError(
                        f"query is not pending in batch: {result['query_id']}"
                    )
                query = _json_value(item["record_json"])
                query["last_attempt"] = result
                metrics["query_attempts"] += 1
                if result["status"] == "completed":
                    metrics["completed_queries"] += 1
                else:
                    metrics["failed_queries"] += 1
                metrics["result_count"] += result["result_count"]
                metrics["discovery_hits"] += len(
                    result.get("discovery_hits", [])
                )
                if result["status"] == "completed":
                    self.record_discovery_hits(
                        cycle_id=cycle_id,
                        query=query,
                        observed_at=executed_at,
                        hits=result.get("discovery_hits", []),
                    )
                    self.connection.execute(
                        "UPDATE query_batch_items SET status = 'completed', record_json = ? "
                        "WHERE batch_id = ? AND query_id = ?",
                        (_json_text(query), batch_id, result["query_id"]),
                    )
                    state = {
                        "schema_version": 1,
                        "query_id": result["query_id"],
                        "topic_id": query["topic_id"],
                        "last_completed_cycle": batch["cycle_id"],
                        "last_completed_at": executed_at,
                        "cursor": result["cursor"],
                        "result_count": result["result_count"],
                        "discovery_hits": result.get("discovery_hits", []),
                        "selected_endpoints": result["selected_endpoints"],
                    }
                    self.connection.execute(
                        "INSERT INTO query_states("
                        "query_id, last_completed_cycle, last_completed_at, cursor, result_count, "
                        "selected_endpoint_count, record_json"
                        ") VALUES(?, ?, ?, ?, ?, ?, ?) "
                        "ON CONFLICT(query_id) DO UPDATE SET "
                        "last_completed_cycle = excluded.last_completed_cycle, "
                        "last_completed_at = excluded.last_completed_at, "
                        "cursor = excluded.cursor, result_count = excluded.result_count, "
                        "selected_endpoint_count = excluded.selected_endpoint_count, "
                        "record_json = excluded.record_json",
                        (
                            result["query_id"],
                            batch["cycle_id"],
                            executed_at,
                            result["cursor"],
                            result["result_count"],
                            len(result["selected_endpoints"]),
                            _json_text(state),
                        ),
                    )
                else:
                    self.connection.execute(
                        "UPDATE query_batch_items SET record_json = ? "
                        "WHERE batch_id = ? AND query_id = ?",
                        (_json_text(query), batch_id, result["query_id"]),
                    )
            pending = int(
                self.connection.execute(
                    "SELECT COUNT(*) FROM query_batch_items "
                    "WHERE batch_id = ? AND status = 'pending'",
                    (batch_id,),
                ).fetchone()[0]
            )
            status = "pending" if pending else "completed"
            record = _json_value(batch["record_json"])
            record["status"] = status
            record["completed_at"] = None if pending else executed_at
            self.connection.execute(
                "UPDATE query_batches SET status = ?, completed_at = ?, record_json = ? "
                "WHERE id = ?",
                (status, record["completed_at"], _json_text(record), batch_id),
            )
            metrics["pending_queries"] = pending
            metrics["discovery_review"] = self.discovery_review_metrics(cycle_id)
            metrics["selected_source_ids"] = metrics["discovery_review"][
                "selected_source_ids"
            ]
            metrics["updated_at"] = executed_at
            self._set_meta(
                f"query_cycle_metrics:{cycle_id}", _json_text(metrics)
            )
        return {
            "status": status,
            "pending_queries": pending,
            "cycle_metrics": metrics,
        }

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
        tier = str(observation["tier"])
        if tier not in TIER_PRIORITY:
            raise RuntimeStoreError("runtime observation has an invalid source tier")
        result = self.connection.execute(
            "INSERT OR IGNORE INTO observations("
            "id, source_id, source_group, topic_id, tier, tier_rank, "
            "source_revision, observed_at, trust, "
            "authority, l0_key, l1_evidence_sha256, record_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation["id"],
                observation["source_id"],
                observation["source_group"],
                observation["topic_id"],
                tier,
                TIER_PRIORITY[tier],
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
            "id, evidence_pack_id, observation_id, source_id, source_group, topic_id, observed_at, trust, "
            "review_status, queue_name, queue_rank, trust_rank, l2_fingerprint_sha256, "
            "l3_recall_count, record_json"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                value["id"],
                value["evidence_pack_id"],
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

    def insert_evidence_pack(self, pack: dict[str, Any]) -> bool:
        result = self.connection.execute(
            "INSERT OR IGNORE INTO evidence_packs("
            "id, batch_id, outcome, reviewed_at, record_json"
            ") VALUES (?, ?, ?, ?, ?)",
            (
                pack["id"],
                pack.get("batch_id"),
                pack["outcome"],
                pack["reviewed_at"],
                _json_text(pack),
            ),
        )
        return result.rowcount == 1

    def commit_semantic_review(
        self,
        *,
        batch_id: str,
        reviewed_at: str,
        packs: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> dict[str, int | str]:
        self.validate()
        candidate_by_pack = {
            candidate["evidence_pack_id"]: candidate for candidate in candidates
        }
        if len(candidate_by_pack) != len(candidates):
            raise RuntimeStoreError("semantic review contains duplicate candidate packs")
        inserted_candidates = 0
        inserted_l3_recalls = 0
        reviewed_observations = 0
        with self.connection:
            batch = self.connection.execute(
                "SELECT status, record_json FROM semantic_batches WHERE id = ?",
                (batch_id,),
            ).fetchone()
            if batch is None or batch["status"] != "pending":
                raise RuntimeStoreError(f"semantic batch is not pending: {batch_id}")
            for pack in packs:
                if pack.get("batch_id") != batch_id:
                    raise RuntimeStoreError("evidence pack references the wrong batch")
                observation_ids = pack.get("observation_ids")
                if not isinstance(observation_ids, list) or not observation_ids:
                    raise RuntimeStoreError("evidence pack needs observation ids")
                placeholders = ",".join("?" for _ in observation_ids)
                rows = self.connection.execute(
                    "SELECT observation_id FROM semantic_batch_items "
                    f"WHERE batch_id = ? AND status = 'pending' AND observation_id IN ({placeholders})",
                    (batch_id, *observation_ids),
                ).fetchall()
                if {str(row["observation_id"]) for row in rows} != set(observation_ids):
                    raise RuntimeStoreError(
                        "evidence pack observations are not pending in the batch"
                    )
                if not self.insert_evidence_pack(pack):
                    raise RuntimeStoreError(f"duplicate evidence pack: {pack['id']}")
                self.connection.execute(
                    "UPDATE semantic_batch_items SET status = 'reviewed', evidence_pack_id = ? "
                    f"WHERE batch_id = ? AND observation_id IN ({placeholders})",
                    (pack["id"], batch_id, *observation_ids),
                )
                reviewed_observations += len(observation_ids)
                candidate = candidate_by_pack.get(pack["id"])
                if pack["outcome"] == "candidate":
                    if candidate is None:
                        raise RuntimeStoreError("candidate evidence pack has no candidate")
                    if not self.insert_candidate(candidate):
                        raise RuntimeStoreError(
                            f"duplicate semantic candidate: {candidate['id']}"
                        )
                    inserted_candidates += 1
                    inserted_l3_recalls += len(candidate["l3_recall"])
                    for source_id in pack["source_ids"]:
                        self.connection.execute(
                            "UPDATE source_utility SET candidates = candidates + 1 "
                            "WHERE source_id = ?",
                            (source_id,),
                        )
                elif candidate is not None:
                    raise RuntimeStoreError(
                        "not-promoted evidence pack cannot create a candidate"
                    )
            pending = self.semantic_batch_pending_count(batch_id)
            status = "pending" if pending else "completed"
            record = _json_value(batch["record_json"])
            record["status"] = status
            record["completed_at"] = None if pending else reviewed_at
            self.connection.execute(
                "UPDATE semantic_batches SET status = ?, completed_at = ?, record_json = ? "
                "WHERE id = ?",
                (status, record["completed_at"], _json_text(record), batch_id),
            )
        return {
            "status": status,
            "reviewed_observations": reviewed_observations,
            "pending_observations": pending,
            "normalized_candidates": inserted_candidates,
            "l3_recalls": inserted_l3_recalls,
        }

    def commit_scan(
        self,
        *,
        now: str,
        source_states: dict[str, dict[str, Any]],
        observations: list[dict[str, Any]],
    ) -> dict[str, int]:
        self.validate()
        inserted_observations = 0
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
            observations_by_source = Counter(
                observation["source_id"] for observation in observations
            )
            for source_id, state in source_states.items():
                utility = state.get("last_request_utility", {})
                self.connection.execute(
                    "INSERT INTO source_utility("
                    "source_id, source_requests, successes, failures, downloaded_bytes, "
                    "observations, candidates"
                    ") VALUES(?, 1, 1, 0, ?, ?, 0) "
                    "ON CONFLICT(source_id) DO UPDATE SET "
                    "source_requests = source_requests + 1, "
                    "successes = successes + 1, "
                    "downloaded_bytes = downloaded_bytes + excluded.downloaded_bytes, "
                    "observations = observations + excluded.observations",
                    (
                        source_id,
                        int(utility.get("downloaded_bytes", 0)),
                        observations_by_source[source_id],
                    ),
                )
            self._set_meta("last_successful_run", now)
        return {
            "observations_inserted": inserted_observations,
            "observation_duplicates": len(observations) - inserted_observations,
            "normalized_candidates": 0,
            "candidate_duplicates": 0,
            "l3_recalls": 0,
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
                    "schema_version": 3,
                    "source_group": "legacy-import",
                    "topic_id": "legacy.reviewed",
                    "tier": (
                        "T2"
                        if discovery.get("trust") == "official"
                        else "T3"
                        if discovery.get("trust") == "representative"
                        else "T4"
                    ),
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
                evidence_pack_id = f"legacy-{candidate_id}"
                evidence_pack = {
                    "schema_version": 1,
                    "id": evidence_pack_id,
                    "batch_id": None,
                    "outcome": "candidate",
                    "reviewed_by": "codex",
                    "reviewed_at": record.get(
                        "reviewed_at", discovery["observed_at"]
                    ),
                    "observation_ids": [candidate_id],
                    "source_ids": [discovery["source_id"]],
                    "necessary_facts": discovery.get("extracted_facts", []),
                    "non_obvious_decisions": [],
                    "license_assessment": "Migrated reviewed legacy evidence.",
                    "risk": {"level": "standard", "domains": []},
                    "adjacent_capabilities": [],
                    "rationale": "Migrated from the reviewed v0.1.1 decision history.",
                }
                if not self.insert_evidence_pack(evidence_pack):
                    raise RuntimeStoreError(
                        f"legacy import contains duplicate evidence pack: {candidate_id}"
                    )
                candidate = {
                    "schema_version": 3,
                    "id": candidate_id,
                    "evidence_pack_id": evidence_pack_id,
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


def upgrade_runtime_v3_to_v4(root: Path) -> dict[str, Any]:
    destination = runtime_store_path(root)
    if not destination.is_file():
        raise RuntimeStoreError("runtime store is missing for schema upgrade")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".harvest-v4-", suffix=".sqlite3", dir=destination.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(destination, temporary)
        with RuntimeStore(temporary) as store:
            version = store.connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if version is None or version["value"] != "3":
                raise RuntimeStoreError(
                    "runtime schema upgrade requires exactly schema version 3"
                )
            with store.connection:
                store.connection.executescript(
                    """
                    CREATE TABLE discovery_hits (
                        id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        first_seen_at TEXT NOT NULL,
                        last_seen_at TEXT NOT NULL,
                        reviewed_at TEXT,
                        selected_source_id TEXT,
                        record_json TEXT NOT NULL
                    );
                    CREATE INDEX discovery_hits_review_page
                        ON discovery_hits (status, first_seen_at, id);
                    CREATE TABLE discovery_hit_occurrences (
                        hit_id TEXT NOT NULL REFERENCES discovery_hits(id),
                        cycle_id TEXT NOT NULL,
                        query_id TEXT NOT NULL,
                        source_group TEXT NOT NULL,
                        topic_id TEXT NOT NULL,
                        observed_at TEXT NOT NULL,
                        PRIMARY KEY (hit_id, cycle_id, query_id)
                    );
                    CREATE INDEX discovery_hit_occurrences_cycle
                        ON discovery_hit_occurrences (cycle_id, hit_id);
                    """
                )
                states = store.connection.execute(
                    "SELECT query_id, last_completed_cycle, last_completed_at, record_json "
                    "FROM query_states ORDER BY query_id"
                ).fetchall()
                for state_row in states:
                    state = _json_value(state_row["record_json"])
                    hits = state.get("discovery_hits", [])
                    if not hits:
                        continue
                    query_row = store.connection.execute(
                        "SELECT query_batch_items.record_json "
                        "FROM query_batch_items JOIN query_batches "
                        "ON query_batches.id = query_batch_items.batch_id "
                        "WHERE query_batch_items.query_id = ? "
                        "AND query_batches.cycle_id = ? "
                        "ORDER BY query_batches.created_at DESC LIMIT 1",
                        (
                            state_row["query_id"],
                            state_row["last_completed_cycle"],
                        ),
                    ).fetchone()
                    if query_row is None:
                        raise RuntimeStoreError(
                            f"query hit migration lacks context: {state_row['query_id']}"
                        )
                    query = _json_value(query_row["record_json"])
                    for field in ("id", "source_group", "topic_id"):
                        if not isinstance(query.get(field), str) or not query[field]:
                            raise RuntimeStoreError(
                                f"query hit migration context is invalid: {state_row['query_id']}"
                            )
                    store.record_discovery_hits(
                        cycle_id=str(state_row["last_completed_cycle"]),
                        query=query,
                        observed_at=str(state_row["last_completed_at"]),
                        hits=hits,
                    )
                store._set_meta("schema_version", str(SCHEMA_VERSION))
            store.validate()
            metrics = store.discovery_review_metrics()
            cycles = [
                str(row["cycle_id"])
                for row in store.connection.execute(
                    "SELECT DISTINCT cycle_id FROM discovery_hit_occurrences "
                    "ORDER BY cycle_id"
                )
            ]
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "schema_version": 1,
        "report_type": "runtime-schema-upgrade",
        "from_schema": 3,
        "to_schema": SCHEMA_VERSION,
        "migrated_hits": metrics["unique_hits"],
        "pending_hits": metrics["pending"],
        "affected_cycles": cycles,
    }


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
        "schema_version": SCHEMA_VERSION,
        "backend": f"sqlite-v{SCHEMA_VERSION}",
        "source_states": len(state["sources"]),
        "observations": len(discoveries),
        "candidates": len(decisions),
        "decisions": len(decisions),
        "legacy_sha256": _legacy_digest(root),
    }
