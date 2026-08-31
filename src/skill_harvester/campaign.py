from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .io import atomic_write_text, load_json
from .runtime_store import open_runtime_store, runtime_store_path
from .sources import FetchResponse, Fetcher, RegistryError, SourceFetchError, load_registry, run_scan


class CampaignPolicyError(ValueError):
    pass


class CampaignStopLoss(RuntimeError):
    pass


STOP_LOSS_INTEGER_FIELDS = (
    "max_source_requests",
    "max_download_bytes",
    "max_runtime_store_bytes",
    "max_observations",
    "max_normalized_candidates",
    "max_l3_recalls",
)


def load_campaign_policy(root: Path) -> dict[str, Any]:
    value = load_json(root / "config" / "campaign-policy.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise CampaignPolicyError("campaign policy must use schema_version 1")
    if value.get("campaign_id") != "first-high-throughput":
        raise CampaignPolicyError("campaign policy id is invalid")
    planned_capacity = value.get("planned_capacity_range")
    if not isinstance(planned_capacity, dict):
        raise CampaignPolicyError("campaign planned capacity is missing")
    for field in ("endpoints", "actual_queries"):
        capacity_range = planned_capacity.get(field)
        if (
            not isinstance(capacity_range, list)
            or len(capacity_range) != 2
            or any(
                not isinstance(item, int) or isinstance(item, bool) or item <= 0
                for item in capacity_range
            )
            or capacity_range[0] > capacity_range[1]
        ):
            raise CampaignPolicyError(f"campaign {field} capacity range is invalid")
    objective = value.get("objective")
    if (
        not isinstance(objective, dict)
        or objective.get("type") != "capacity-lower-bound"
        or set(objective) != {"type", "controller_end"}
    ):
        raise CampaignPolicyError("campaign objective is invalid")
    controller_end = objective["controller_end"]
    if controller_end is not None and (
        not isinstance(controller_end, dict)
        or set(controller_end) != {"ended_at", "reason"}
        or any(
            not isinstance(controller_end.get(field), str)
            or not controller_end[field].strip()
            for field in ("ended_at", "reason")
        )
    ):
        raise CampaignPolicyError("campaign controller end is invalid")
    groups = value.get("source_groups")
    if not isinstance(groups, dict) or not groups:
        raise CampaignPolicyError("campaign policy must contain source groups")
    source_ids: set[str] = set()
    for group in groups.values():
        if (
            not isinstance(group, dict)
            or not isinstance(group.get("topic_id"), str)
            or not group["topic_id"]
            or not isinstance(group.get("source_ids"), list)
            or not group["source_ids"]
            or any(not isinstance(source_id, str) for source_id in group["source_ids"])
        ):
            raise CampaignPolicyError("campaign source group is invalid")
        overlap = source_ids.intersection(group["source_ids"])
        if overlap:
            raise CampaignPolicyError("campaign source ids must belong to one group")
        source_ids.update(group["source_ids"])
    canary = value.get("canary_source_ids")
    if (
        not isinstance(canary, list)
        or not canary
        or any(not isinstance(source_id, str) for source_id in canary)
        or len(canary) != len(set(canary))
    ):
        raise CampaignPolicyError("campaign canary source ids are invalid")
    if not set(canary) <= source_ids:
        raise CampaignPolicyError("campaign canary references an unknown source")
    if value.get("queue_order") != [
        "urgent-impact",
        "official-gap",
        "reactivation",
        "novel-discovery",
        "aged-backlog",
    ]:
        raise CampaignPolicyError("campaign queue order is invalid")
    stop_loss = value.get("stop_loss")
    if not isinstance(stop_loss, dict):
        raise CampaignPolicyError("campaign stop-loss is missing")
    if (
        not isinstance(stop_loss.get("minimum_source_requests"), int)
        or stop_loss["minimum_source_requests"] <= 0
        or not isinstance(stop_loss.get("minimum_source_success_rate"), (int, float))
        or isinstance(stop_loss["minimum_source_success_rate"], bool)
        or not 0 < stop_loss["minimum_source_success_rate"] <= 1
        or any(
            not isinstance(stop_loss.get(field), int)
            or isinstance(stop_loss[field], bool)
            or stop_loss[field] <= 0
            for field in STOP_LOSS_INTEGER_FIELDS
        )
        or not isinstance(stop_loss.get("max_usage_credits"), (int, float))
        or isinstance(stop_loss["max_usage_credits"], bool)
        or stop_loss["max_usage_credits"] <= 0
    ):
        raise CampaignPolicyError("campaign stop-loss is invalid")
    if stop_loss["minimum_source_requests"] > len(canary):
        raise CampaignPolicyError("campaign canary cannot meet its minimum request sample")
    minimum_canary = max(
        stop_loss["minimum_source_requests"], (len(source_ids) + 19) // 20
    )
    maximum_canary = max(
        stop_loss["minimum_source_requests"], (len(source_ids) + 9) // 10
    )
    if not minimum_canary <= len(canary) <= maximum_canary:
        raise CampaignPolicyError(
            "campaign canary must cover 5-10 percent of registered endpoints"
        )
    return value


def campaign_source_context(policy: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        source_id: {"source_group": group_name, "topic_id": group["topic_id"]}
        for group_name, group in policy["source_groups"].items()
        for source_id in group["source_ids"]
    }


def _ordered_source_ids(policy: dict[str, Any]) -> list[str]:
    return [
        source_id
        for group in policy["source_groups"].values()
        for source_id in group["source_ids"]
    ]


def _run_time(now: str, offset: int) -> str:
    try:
        value = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as error:
        raise CampaignPolicyError("campaign timestamp must be ISO 8601") from error
    return (value.astimezone(timezone.utc) + timedelta(microseconds=offset)).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


class _BudgetedFetcher:
    def __init__(self, delegate: Fetcher, stop_loss: dict[str, Any]) -> None:
        self.delegate = delegate
        self.stop_loss = stop_loss
        self.source_requests = 0
        self.downloaded_bytes = 0

    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        if self.source_requests >= self.stop_loss["max_source_requests"]:
            raise CampaignStopLoss("max_source_requests reached")
        self.source_requests += 1
        response = self.delegate.fetch(url, headers)
        self.downloaded_bytes += len(response.body)
        if self.downloaded_bytes > self.stop_loss["max_download_bytes"]:
            raise CampaignStopLoss("max_download_bytes reached")
        return response


def _aggregate_metrics(
    root: Path,
    runs: list[dict[str, Any]],
    fetcher: _BudgetedFetcher,
    failures: int,
) -> dict[str, Any]:
    with open_runtime_store(root) as store:
        pending_queue = store.candidate_status_counts().get("pending", 0)
    return {
        "source_requests": fetcher.source_requests,
        "source_successes": len(runs),
        "source_success_rate": (
            len(runs) / fetcher.source_requests if fetcher.source_requests else 0.0
        ),
        "failures": failures,
        "raw_observations": sum(
            run["metrics"]["raw_observations"] for run in runs
        ),
        "observations_inserted": sum(
            run["metrics"]["observations_inserted"] for run in runs
        ),
        "observation_duplicates": sum(
            run["metrics"]["observation_duplicates"] for run in runs
        ),
        "normalized_candidates": sum(
            run["metrics"]["normalized_candidates"] for run in runs
        ),
        "candidate_duplicates": sum(
            run["metrics"]["candidate_duplicates"] for run in runs
        ),
        "pending_queue": pending_queue,
        "l3_recalls": sum(run["metrics"]["l3_recalls"] for run in runs),
        "downloaded_bytes": fetcher.downloaded_bytes,
        "runtime_store_bytes": runtime_store_path(root).stat().st_size,
        "deep_reviews": {"measured": False},
        "usage_credits": {"measured": False},
    }


def _budget_reason(
    root: Path, metrics: dict[str, Any], stop_loss: dict[str, Any]
) -> str | None:
    checks = (
        ("source_requests", "max_source_requests"),
        ("downloaded_bytes", "max_download_bytes"),
        ("runtime_store_bytes", "max_runtime_store_bytes"),
        ("raw_observations", "max_observations"),
        ("normalized_candidates", "max_normalized_candidates"),
        ("l3_recalls", "max_l3_recalls"),
    )
    for metric, limit in checks:
        current = (
            runtime_store_path(root).stat().st_size
            if metric == "runtime_store_bytes"
            else metrics[metric]
        )
        if current >= stop_loss[limit]:
            return f"{limit} reached"
    return None


def _write_campaign_report(root: Path, now: str, report: dict[str, Any]) -> None:
    atomic_write_text(
        root / "runs" / f"{now.replace(':', '-')}-campaign.json",
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def run_campaign(
    root: Path,
    fetcher: Fetcher,
    *,
    now: str,
    ramp: bool,
) -> dict[str, Any]:
    policy = load_campaign_policy(root)
    registered = {source["id"] for source in load_registry(root)}
    ordered = _ordered_source_ids(policy)
    unknown = set(ordered) - registered
    if unknown:
        raise RegistryError(
            f"campaign policy references unknown source ids: {', '.join(sorted(unknown))}"
        )
    contexts = campaign_source_context(policy)
    canary_ids = list(policy["canary_source_ids"])
    remaining_ids = [source_id for source_id in ordered if source_id not in canary_ids]
    budgeted = _BudgetedFetcher(fetcher, policy["stop_loss"])
    runs: list[dict[str, Any]] = []
    completed: list[str] = []
    stop_reasons: list[str] = []
    failures = 0
    failure: dict[str, str] | None = None

    phases = [("canary", canary_ids)]
    if ramp:
        phases.append(("ramp", remaining_ids))
    for phase, source_ids in phases:
        if stop_reasons:
            break
        if phase == "ramp":
            canary_metrics = _aggregate_metrics(root, runs, budgeted, failures)
            if len(completed) < policy["stop_loss"]["minimum_source_requests"]:
                stop_reasons.append("canary did not meet its minimum source-request sample")
                break
            if (
                canary_metrics["source_success_rate"]
                < policy["stop_loss"]["minimum_source_success_rate"]
            ):
                stop_reasons.append("source success rate crossed stop-loss")
                break
        for source_id in source_ids:
            metrics = _aggregate_metrics(root, runs, budgeted, failures)
            reason = _budget_reason(root, metrics, policy["stop_loss"])
            if reason is not None:
                stop_reasons.append(reason)
                break
            try:
                scan_report = run_scan(
                    root,
                    budgeted,
                    now=_run_time(now, len(runs)),
                    source_ids={source_id},
                    source_context={source_id: contexts[source_id]},
                    persist_report=False,
                )
            except CampaignStopLoss as error:
                stop_reasons.append(str(error))
                failure = {
                    "phase": phase,
                    "source_id": source_id,
                    "error": f"{type(error).__name__}: {error}",
                }
                break
            except (RegistryError, SourceFetchError, OSError) as error:
                failures += 1
                stop_reasons.append(f"{phase} source failure")
                failure = {
                    "phase": phase,
                    "source_id": source_id,
                    "error": f"{type(error).__name__}: {error}",
                }
                break
            scan_report["campaign_phase"] = phase
            runs.append(scan_report)
            completed.append(source_id)
            metrics = _aggregate_metrics(root, runs, budgeted, failures)
            reason = _budget_reason(root, metrics, policy["stop_loss"])
            if reason is not None:
                stop_reasons.append(reason)
                break

    if not ramp and not stop_reasons:
        stop_reasons.append("ramp not requested")

    metrics = _aggregate_metrics(root, runs, budgeted, failures)
    selected_for_run = canary_ids + (remaining_ids if ramp else [])
    pending = [source_id for source_id in selected_for_run if source_id not in completed]
    if stop_reasons:
        status = "checkpoint"
    elif metrics["observations_inserted"] or metrics["normalized_candidates"]:
        status = "changed"
    else:
        status = "no_op"
    with open_runtime_store(root) as store:
        last_successful_run = store.last_successful_run()
    report: dict[str, Any] = {
        "schema_version": 2,
        "report_type": "campaign",
        "campaign_id": policy["campaign_id"],
        "run_id": now.replace(":", "-"),
        "planned_capacity_range": policy["planned_capacity_range"],
        "registered_endpoints": len(ordered),
        "canary_endpoints": len(canary_ids),
        "canary_completed": set(canary_ids) <= set(completed),
        "ramped": ramp and not stop_reasons and not pending,
        "status": status,
        "stop_reasons": stop_reasons,
        "checkpoint": {
            "completed_source_ids": completed,
            "pending_source_ids": pending,
            "last_successful_run": last_successful_run,
        },
        "metrics": metrics,
        "runs": runs,
    }
    if failure is not None:
        report["failure"] = failure
    _write_campaign_report(root, now, report)
    return report
