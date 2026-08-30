from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .campaign import load_campaign_policy
from .io import atomic_write_json, load_json
from .runtime_store import open_runtime_store


class ProductionReportError(ValueError):
    pass


def _report(path: Path, report_type: str, schema_version: int) -> dict[str, Any]:
    value = load_json(path)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != schema_version
        or value.get("report_type") != report_type
    ):
        raise ProductionReportError(
            f"{path.name} must be a {report_type} schema {schema_version} report"
        )
    return value


def _relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ProductionReportError("production report inputs must be inside the repository")
    return resolved.relative_to(root.resolve()).as_posix()


def build_production_report(
    root: Path,
    *,
    generated_at: str,
    campaign_report_path: Path,
    query_report_paths: list[Path],
    semantic_report_paths: list[Path],
    supplemental_scan_paths: list[Path],
    query_no_op_report_path: Path,
    semantic_no_op_report_path: Path,
    stable_no_op_scan_path: Path,
) -> dict[str, Any]:
    root = root.resolve()
    policy = load_campaign_policy(root)
    campaign = _report(campaign_report_path, "campaign", 2)
    if (
        campaign.get("campaign_id") != policy["campaign_id"]
        or campaign.get("planned_capacity_range")
        != policy["planned_capacity_range"]
    ):
        raise ProductionReportError(
            "campaign report objective must match the repository campaign policy"
        )
    if not query_report_paths:
        raise ProductionReportError("at least one query report is required")
    query_reports = [
        _report(path, "query-results", 1) for path in query_report_paths
    ]
    query_no_op = _report(query_no_op_report_path, "query-export", 1)
    semantic_no_op = _report(semantic_no_op_report_path, "semantic-export", 1)
    stable_no_op_scan = _report(stable_no_op_scan_path, "scan", 2)
    if (
        query_no_op.get("status") != "no_op"
        or query_no_op.get("exported_queries") != 0
        or semantic_no_op.get("status") != "no_op"
        or semantic_no_op.get("exported_observations") != 0
        or stable_no_op_scan.get("status") != "no_op"
        or stable_no_op_scan["metrics"]["observations_inserted"] != 0
    ):
        raise ProductionReportError("replay reports must prove query, semantic, and stable-source no-op")
    raw_cycle_ids = [report.get("cycle_id") for report in query_reports]
    if (
        any(not isinstance(cycle_id, str) or not cycle_id for cycle_id in raw_cycle_ids)
        or len(set(raw_cycle_ids)) != 1
        or query_no_op.get("cycle_id") != raw_cycle_ids[0]
    ):
        raise ProductionReportError(
            "query reports and no-op proof must belong to one explicit cycle"
        )
    query_cycle_ids = [raw_cycle_ids[0]]
    if not semantic_report_paths:
        raise ProductionReportError("at least one semantic report is required")
    semantic_reports = [
        _report(path, "semantic-review", 1) for path in semantic_report_paths
    ]
    supplemental_scans = [
        _report(path, "scan", 2) for path in supplemental_scan_paths
    ]
    batch_ids = list(dict.fromkeys(report["batch_id"] for report in semantic_reports))
    with open_runtime_store(root) as store:
        batches = [store.semantic_batch(batch_id) for batch_id in batch_ids]
        batch_items = [
            item
            for batch_id in batch_ids
            for item in store.semantic_batch_items(batch_id)
        ]
        packs = [
            pack
            for batch_id in batch_ids
            for pack in store.evidence_packs_for_batch(batch_id)
        ]
        candidates = store.candidates_for_evidence_packs(
            {pack["id"] for pack in packs}
        )
        decisions = store.decisions_for_candidates(
            {candidate["id"] for candidate in candidates}
        )
    outcomes = Counter(decision["outcome"] for decision in decisions)
    latest_query_reports: dict[str, dict[str, Any]] = {}
    for report in sorted(query_reports, key=lambda value: value["executed_at"]):
        latest_query_reports[report["batch_id"]] = report
    pending_queries = sum(
        report["pending_queries"] for report in latest_query_reports.values()
    )
    selected_source_ids = sorted(
        {
            source_id
            for report in query_reports
            for source_id in report["selected_source_ids"]
        }
    )
    pending_candidates = sum(
        candidate["review_status"] == "pending" for candidate in candidates
    )
    pending_semantic = sum(item["status"] == "pending" for item in batch_items)
    has_pending_work = bool(pending_queries or pending_semantic or pending_candidates)
    stop_reasons = campaign.get("stop_reasons")
    if not isinstance(stop_reasons, list) or any(
        not isinstance(reason, str) or not reason for reason in stop_reasons
    ):
        raise ProductionReportError("campaign stop reasons are invalid")
    stop_loss_triggered = campaign.get("status") == "checkpoint" or bool(stop_reasons)
    executable_endpoints = campaign["registered_endpoints"] + len(selected_source_ids)
    actual_queries = sum(report["completed_queries"] for report in query_reports)
    minimum_endpoints = policy["planned_capacity_range"]["endpoints"][0]
    minimum_queries = policy["planned_capacity_range"]["actual_queries"][0]
    objective_met = (
        executable_endpoints >= minimum_endpoints
        and actual_queries >= minimum_queries
    )
    controller_end = policy["objective"]["controller_end"]
    completion_basis = (
        "objective" if objective_met else "controller" if controller_end else None
    )
    slice_checkpoint = has_pending_work or stop_loss_triggered
    if slice_checkpoint:
        campaign_status = "checkpoint"
    elif completion_basis is not None:
        campaign_status = "campaign_completed"
    else:
        campaign_status = "active"
    if stop_loss_triggered:
        continuation = (
            "Resume from the persisted checkpoint after resolving the recorded "
            "stop-loss; unprocessed work retains its cursor."
        )
    elif has_pending_work:
        continuation = (
            "Resume the persisted query, semantic, or L4 checkpoint before "
            "starting another batch."
        )
    elif campaign_status == "campaign_completed":
        continuation = "The explicit parent-campaign completion condition is satisfied."
    else:
        continuation = (
            "The current slice is complete; start the next inventory/query batch "
            "from persisted cursors."
        )
    return {
        "schema_version": 1,
        "report_type": "content-production",
        "generated_at": generated_at,
        "status": campaign_status,
        "objective": {
            "type": policy["objective"]["type"],
            "minimum_executable_endpoints": minimum_endpoints,
            "minimum_actual_queries": minimum_queries,
            "met": objective_met,
            "controller_end": controller_end,
            "completion_basis": completion_basis,
        },
        "slice": {
            "status": "checkpoint" if slice_checkpoint else "complete",
            "pending_queries": pending_queries,
            "pending_semantic_observations": pending_semantic,
            "pending_l4_candidates": pending_candidates,
        },
        "inputs": {
            "campaign_report": _relative(root, campaign_report_path),
            "query_reports": [
                _relative(root, path) for path in query_report_paths
            ],
            "semantic_reports": [
                _relative(root, path) for path in semantic_report_paths
            ],
            "supplemental_scans": [
                _relative(root, path) for path in supplemental_scan_paths
            ],
            "query_no_op_report": _relative(root, query_no_op_report_path),
            "semantic_no_op_report": _relative(root, semantic_no_op_report_path),
            "stable_no_op_scan": _relative(root, stable_no_op_scan_path),
        },
        "discovery": {
            "endpoints_at_campaign_start": campaign["registered_endpoints"],
            "selected_new_endpoints": len(selected_source_ids),
            "executable_endpoints_after_selection": executable_endpoints,
            "supplemental_source_runs": len(supplemental_scans),
            "source_requests": campaign["metrics"]["source_requests"]
            + sum(scan["metrics"]["source_requests"] for scan in supplemental_scans),
            "source_successes": campaign["metrics"]["source_successes"]
            + sum(scan["metrics"]["sources_succeeded"] for scan in supplemental_scans),
            "downloaded_bytes": campaign["metrics"]["downloaded_bytes"]
            + sum(scan["metrics"]["downloaded_bytes"] for scan in supplemental_scans),
            "raw_observations": campaign["metrics"]["raw_observations"]
            + sum(scan["metrics"]["raw_observations"] for scan in supplemental_scans),
            "inserted_observations": campaign["metrics"]["observations_inserted"]
            + sum(scan["metrics"]["observations_inserted"] for scan in supplemental_scans),
            "source_failures": campaign["metrics"]["failures"]
            + sum(scan["metrics"]["failures"] for scan in supplemental_scans),
        },
        "queries": {
            "cycle_ids": query_cycle_ids,
            "batch_ids": sorted(latest_query_reports),
            "actual_queries": actual_queries,
            "query_attempts": sum(report["actual_queries"] for report in query_reports),
            "completed_queries": sum(
                report["completed_queries"] for report in query_reports
            ),
            "failed_attempts": sum(
                report["failed_queries"] for report in query_reports
            ),
            "pending_queries": pending_queries,
            "result_count": sum(report["result_count"] for report in query_reports),
            "discovery_hits": sum(
                report.get("discovery_hits", 0) for report in query_reports
            ),
            "selected_endpoints": len(selected_source_ids),
            "selected_source_ids": selected_source_ids,
        },
        "semantic": {
            "batch_ids": batch_ids,
            "batch_statuses": [batch["status"] for batch in batches],
            "batch_observations": len(batch_items),
            "reviewed_observations": sum(
                item["status"] == "reviewed" for item in batch_items
            ),
            "pending_observations": sum(
                item["status"] == "pending" for item in batch_items
            ),
            "evidence_packs": len(packs),
            "not_promoted": sum(pack["outcome"] == "not_promoted" for pack in packs),
            "normalized_candidates": len(candidates),
            "l2_matches": sum(len(candidate["l2_matches"]) for candidate in candidates),
            "l3_recalls": sum(len(candidate["l3_recall"]) for candidate in candidates),
        },
        "l4": {
            "deep_reviews": {"measured": True, "count": len(decisions)},
            "pending_candidates": pending_candidates,
            "not_promoted": outcomes["not_promoted"],
            "merge": outcomes["merge"],
            "update": outcomes["update"],
            "create": outcomes["create"],
        },
        "artifacts": {
            "new_skills": outcomes["create"],
            "updated_skills": outcomes["update"],
            "release_published": False,
        },
        "replay": {
            "query_rotation": "no_op",
            "semantic_batches": "no_op",
            "stable_source": stable_no_op_scan["sources"][0]["source_id"],
            "stable_source_result": "no_op",
        },
        "cost": {
            "usage_credits": {"measured": False},
            "semantic_review_tokens": {"measured": False},
        },
        "checkpoint": {
            "pending_queries": pending_queries,
            "pending_semantic_observations": sum(
                item["status"] == "pending" for item in batch_items
            ),
            "pending_l4_candidates": pending_candidates,
            "stop_loss": {
                "triggered": stop_loss_triggered,
                "reasons": stop_reasons,
            },
            "continuation": continuation,
        },
    }


def write_production_report(
    root: Path,
    *,
    generated_at: str,
    campaign_report_path: Path,
    query_report_paths: list[Path],
    semantic_report_paths: list[Path],
    supplemental_scan_paths: list[Path],
    query_no_op_report_path: Path,
    semantic_no_op_report_path: Path,
    stable_no_op_scan_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    report = build_production_report(
        root,
        generated_at=generated_at,
        campaign_report_path=campaign_report_path,
        query_report_paths=query_report_paths,
        semantic_report_paths=semantic_report_paths,
        supplemental_scan_paths=supplemental_scan_paths,
        query_no_op_report_path=query_no_op_report_path,
        semantic_no_op_report_path=semantic_no_op_report_path,
        stable_no_op_scan_path=stable_no_op_scan_path,
    )
    atomic_write_json(output_path, report)
    return report
