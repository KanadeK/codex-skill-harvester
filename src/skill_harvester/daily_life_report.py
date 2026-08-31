from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .io import load_json
from .runtime_store import open_runtime_store
from .scenario_bank import load_scenario_bank
from .sources import load_registry


class DailyLifeReportError(ValueError):
    pass


CYCLE_ID = "daily-life-pilot-2026-08-30"


def _relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise DailyLifeReportError("Daily Life report input escapes the repository")
    return resolved.relative_to(root.resolve()).as_posix()


def _replay(path: Path, report_type: str) -> dict[str, Any]:
    value = load_json(path)
    if (
        not isinstance(value, dict)
        or value.get("report_type") != report_type
        or value.get("status") != "no_op"
    ):
        raise DailyLifeReportError(f"{path.name} is not a {report_type} no-op report")
    return value


def build_daily_life_report(
    root: Path,
    *,
    generated_at: str,
    query_no_op_path: Path,
    semantic_no_op_path: Path,
    stable_scan_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    query_no_op = _replay(query_no_op_path, "query-export")
    semantic_no_op = _replay(semantic_no_op_path, "semantic-export")
    stable_scan = _replay(stable_scan_path, "scan")
    if (
        query_no_op.get("cycle_id") != CYCLE_ID
        or query_no_op.get("exported_queries") != 0
        or semantic_no_op.get("exported_observations") != 0
        or stable_scan.get("metrics", {}).get("observations_inserted") != 0
    ):
        raise DailyLifeReportError("Daily Life replay reports do not prove no-op")

    query = load_json(root / "runs" / f"{CYCLE_ID}-queries.json")
    if (
        not isinstance(query, dict)
        or query.get("report_type") != "query-results"
        or query.get("aggregation") != "cycle"
        or query.get("cycle_id") != CYCLE_ID
    ):
        raise DailyLifeReportError("Daily Life query summary is invalid")
    source_config = load_json(root / "config" / "daily-life-sources.json")
    if (
        not isinstance(source_config, dict)
        or source_config.get("schema_version") != 1
        or not isinstance(source_config.get("sources"), list)
        or not source_config["sources"]
    ):
        raise DailyLifeReportError("Daily Life source metadata is invalid")
    selected_source_ids = [record["source_id"] for record in source_config["sources"]]
    if len(selected_source_ids) != len(set(selected_source_ids)):
        raise DailyLifeReportError("Daily Life source metadata contains duplicate ids")
    registry_ids = {source["id"] for source in load_registry(root)}
    if not set(selected_source_ids) <= registry_ids:
        raise DailyLifeReportError("Daily Life source metadata references unknown sources")

    with open_runtime_store(root) as store:
        discovery = store.discovery_review_metrics(CYCLE_ID)
        if sorted(selected_source_ids) != discovery["selected_source_ids"]:
            raise DailyLifeReportError(
                "Daily Life selected sources disagree with discovery review"
            )
        scanned = sum(bool(store.source_state(source_id)) for source_id in selected_source_ids)
        placeholders = ",".join("?" for _ in selected_source_ids)
        utilities = store.connection.execute(
            "SELECT source_id, source_requests, successes, failures, downloaded_bytes, "
            "observations, candidates FROM source_utility "
            f"WHERE source_id IN ({placeholders}) ORDER BY source_id",
            tuple(selected_source_ids),
        ).fetchall()
        observation_rows = store.connection.execute(
            "SELECT id FROM observations WHERE source_group LIKE 'daily-life-%' "
            "ORDER BY id"
        ).fetchall()
        observation_ids = {str(row["id"]) for row in observation_rows}
        pack_rows = store.connection.execute(
            "SELECT DISTINCT evidence_packs.record_json FROM evidence_packs "
            "JOIN semantic_batch_items ON semantic_batch_items.evidence_pack_id = evidence_packs.id "
            "JOIN observations ON observations.id = semantic_batch_items.observation_id "
            "WHERE observations.source_group LIKE 'daily-life-%'"
        ).fetchall()
        packs = [load_json_value(row["record_json"]) for row in pack_rows]
        pack_ids = {pack["id"] for pack in packs}
        candidate_rows = store.connection.execute(
            "SELECT record_json FROM candidates ORDER BY id"
        ).fetchall()
        candidates = [
            load_json_value(row["record_json"])
            for row in candidate_rows
            if load_json_value(row["record_json"])["evidence_pack_id"] in pack_ids
        ]
        candidate_ids = {candidate["id"] for candidate in candidates}
        decision_rows = store.connection.execute(
            "SELECT candidate_id, record_json FROM decisions ORDER BY candidate_id"
        ).fetchall()
        decisions = [
            load_json_value(row["record_json"])
            for row in decision_rows
            if str(row["candidate_id"]) in candidate_ids
        ]
        pending_semantic = int(
            store.connection.execute(
                "SELECT COUNT(*) FROM observations LEFT JOIN semantic_batch_items "
                "ON semantic_batch_items.observation_id = observations.id "
                "WHERE observations.source_group LIKE 'daily-life-%' "
                "AND (semantic_batch_items.status IS NULL OR semantic_batch_items.status != 'reviewed')"
            ).fetchone()[0]
        )
        hit_rows = store.connection.execute(
            "SELECT DISTINCT discovery_hits.record_json FROM discovery_hits "
            "JOIN discovery_hit_occurrences ON discovery_hit_occurrences.hit_id = discovery_hits.id "
            "WHERE discovery_hit_occurrences.cycle_id = ?",
            (CYCLE_ID,),
        ).fetchall()
        failed_source_ids = sorted(
            {
                review["selected_endpoint"]["source_id"]
                for row in hit_rows
                for review in load_json_value(row["record_json"]).get(
                    "review_history", []
                )
                if review.get("outcome") == "selected_endpoint"
            }
        )

    utility_totals = {
        "requests": sum(int(row["source_requests"]) for row in utilities),
        "successes": sum(int(row["successes"]) for row in utilities),
        "failures": sum(int(row["failures"]) for row in utilities),
        "downloaded_bytes": sum(int(row["downloaded_bytes"]) for row in utilities),
        "observations": sum(int(row["observations"]) for row in utilities),
    }
    scenario_report = load_scenario_bank(root)
    regions = Counter(record["region"] for record in source_config["sources"])
    languages = Counter(record["language"] for record in source_config["sources"])
    family_sources = Counter(record["family"] for record in source_config["sources"])
    catalog = load_json(root / "catalog" / "capabilities.json")
    daily_entries = [
        entry
        for entry in catalog["internal"]
        if "daily-life" in entry["classification"]["facets"]["domain"]
    ]
    plugin_ids = sorted({entry["plugin_id"] for entry in daily_entries})
    eval_paths = sorted((root / "evals" / "daily-life").glob("*.json"))
    eval_scenarios = 0
    for path in eval_paths:
        value = load_json(path)
        if (
            not isinstance(value, dict)
            or value.get("method") != "codex-reviewed-instruction-only-scenarios"
            or value.get("reviewed_by") != "codex"
            or value.get("end_to_end", {}).get("kind")
            != "instruction-only-scenarios"
        ):
            raise DailyLifeReportError(f"Daily Life eval is invalid: {path.name}")
        eval_scenarios += len(value["end_to_end"]["scenarios"])
    outcomes = Counter(decision["outcome"] for decision in decisions)
    pending_l4 = sum(candidate["review_status"] == "pending" for candidate in candidates)
    pending = {
        "discovery_hits": discovery["pending"],
        "semantic_observations": pending_semantic,
        "l4_candidates": pending_l4,
    }
    status = "complete" if not any(pending.values()) and scenario_report["pending"] == 0 else "checkpoint"
    return {
        "schema_version": 1,
        "report_type": "daily-life-pilot",
        "generated_at": generated_at,
        "status": status,
        "inputs": {
            "query_summary": f"runs/{CYCLE_ID}-queries.json",
            "query_no_op": _relative(root, query_no_op_path),
            "semantic_no_op": _relative(root, semantic_no_op_path),
            "stable_source_no_op": _relative(root, stable_scan_path),
            "scenario_bank": "catalog/scenario-bank.json",
            "source_metadata": "config/daily-life-sources.json",
        },
        "queries": {
            "completed": query["completed_queries"],
            "attempts": query["query_attempts"],
            "failures": query["failed_queries"],
            "result_count": query["result_count"],
        },
        "discovery_hits": discovery,
        "sources": {
            "selected": len(selected_source_ids),
            "scanned": scanned,
            "selection_failures": len(failed_source_ids),
            "selection_failure_source_ids": failed_source_ids,
            "requests": utility_totals["requests"],
            "successes": utility_totals["successes"],
            "failures": utility_totals["failures"],
            "downloaded_bytes": utility_totals["downloaded_bytes"],
            "observations": utility_totals["observations"],
            "by_family": dict(sorted(family_sources.items())),
            "by_region": dict(sorted(regions.items())),
            "by_language": dict(sorted(languages.items())),
        },
        "semantic": {
            "observations": len(observation_ids),
            "evidence_packs": len(packs),
            "not_promoted_evidence_packs": sum(
                pack["outcome"] == "not_promoted" for pack in packs
            ),
            "normalized_candidates": len(candidates),
            "l2_matches": sum(len(candidate["l2_matches"]) for candidate in candidates),
            "l3_recalls": sum(len(candidate["l3_recall"]) for candidate in candidates),
        },
        "l4": {
            "not_promoted": outcomes["not_promoted"],
            "merge": outcomes["merge"],
            "update": outcomes["update"],
            "create": outcomes["create"],
        },
        "scenarios": {
            "total": scenario_report["scenarios"],
            "by_family": scenario_report["by_family"],
            "outcomes": scenario_report["outcomes"],
            "pending": scenario_report["pending"],
        },
        "artifacts": {
            "plugins": len(plugin_ids),
            "skills": len(daily_entries),
            "release_published": False,
        },
        "evals": {
            "files": len(eval_paths),
            "instruction_scenarios": eval_scenarios,
            "modes_per_skill": ["plan", "live", "recovery"],
        },
        "risk": {
            "not_promoted_evidence_packs": sum(
                pack["outcome"] == "not_promoted" for pack in packs
            ),
            "not_promoted_scenarios": scenario_report["outcomes"].get(
                "not_promoted", 0
            ),
            "automatic_high_risk_publication": "blocked",
        },
        "replay": {
            "query": "no_op",
            "semantic": "no_op",
            "stable_source": stable_scan["sources"][0]["source_id"],
            "stable_source_result": "no_op",
        },
        "usage": {
            "credits": {"measured": False},
            "semantic_review_tokens": {"measured": False},
        },
        "pending": pending,
        "checkpoint": {
            "continuation": (
                "Start the next explicit Daily Life discovery cycle from SQLite cursors."
                if status == "complete"
                else "Resume the non-zero persisted Daily Life stage before another cycle."
            )
        },
    }


def load_json_value(value: str) -> dict[str, Any]:
    result = json.loads(value)
    if not isinstance(result, dict):
        raise DailyLifeReportError("SQLite JSON record is invalid")
    return result
