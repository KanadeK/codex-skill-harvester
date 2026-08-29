from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .io import atomic_write_text, load_json
from .runtime_store import runtime_store_path
from .sources import Fetcher, RegistryError, SourceFetchError, load_registry, run_scan


class CampaignPolicyError(ValueError):
    pass


def load_campaign_policy(root: Path) -> dict[str, Any]:
    value = load_json(root / "config" / "campaign-policy.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise CampaignPolicyError("campaign policy must use schema_version 1")
    if value.get("campaign_id") != "first-high-throughput":
        raise CampaignPolicyError("campaign policy id is invalid")
    groups = value.get("source_groups")
    if not isinstance(groups, dict) or set(groups) != {
        "openai-format-authority",
        "github-delivery",
        "python-packaging",
    }:
        raise CampaignPolicyError("campaign policy source groups are incomplete")
    source_ids: set[str] = set()
    for group in groups.values():
        if (
            not isinstance(group, dict)
            or not isinstance(group.get("topic_id"), str)
            or not isinstance(group.get("source_ids"), list)
            or not group["source_ids"]
            or any(not isinstance(source_id, str) for source_id in group["source_ids"])
        ):
            raise CampaignPolicyError("campaign source group is invalid")
        source_ids.update(group["source_ids"])
    canary = value.get("canary_source_ids")
    if not isinstance(canary, list) or set(canary) != {
        "openai-build-skills",
        "github-cli-release-view",
        "pypi-updates",
    }:
        raise CampaignPolicyError("campaign canary must cover the three source groups")
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
        or not 0 < stop_loss["minimum_source_success_rate"] <= 1
        or any(
            not isinstance(stop_loss.get(field), int) or stop_loss[field] <= 0
            for field in ("max_source_requests", "max_download_bytes", "max_runtime_store_bytes")
        )
    ):
        raise CampaignPolicyError("campaign stop-loss is invalid")
    return value


def _selected_source_ids(policy: dict[str, Any]) -> set[str]:
    return {
        source_id
        for group in policy["source_groups"].values()
        for source_id in group["source_ids"]
    }


def _healthy(report: dict[str, Any], root: Path, policy: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    metrics = report["metrics"]
    stop_loss = policy["stop_loss"]
    if metrics["sources_selected"] < stop_loss["minimum_source_requests"]:
        reasons.append("canary did not meet its minimum source-request sample")
    if metrics["source_success_rate"] < stop_loss["minimum_source_success_rate"]:
        reasons.append("source success rate crossed stop-loss")
    if metrics["downloaded_bytes"] > stop_loss["max_download_bytes"]:
        reasons.append("download volume crossed stop-loss")
    if runtime_store_path(root).stat().st_size > stop_loss["max_runtime_store_bytes"]:
        reasons.append("runtime SQLite store size crossed stop-loss")
    return not reasons, reasons


def _ramp_time(now: str) -> str:
    try:
        value = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as error:
        raise CampaignPolicyError("campaign timestamp must be ISO 8601") from error
    return (value.astimezone(timezone.utc) + timedelta(microseconds=1)).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def run_campaign(
    root: Path,
    fetcher: Fetcher,
    *,
    now: str,
    ramp: bool,
) -> dict[str, Any]:
    policy = load_campaign_policy(root)
    registered = {source["id"] for source in load_registry(root)}
    selected = _selected_source_ids(policy)
    unknown = selected - registered
    if unknown:
        raise RegistryError(f"campaign policy references unknown source ids: {', '.join(sorted(unknown))}")
    canary_ids = set(policy["canary_source_ids"])
    canary = run_scan(root, fetcher, now=now, source_ids=canary_ids)
    healthy, stop_reasons = _healthy(canary, root, policy)
    ramp_report: dict[str, Any] | None = None
    ramp_error: str | None = None
    if ramp and healthy:
        remaining = selected - canary_ids
        if remaining:
            try:
                ramp_report = run_scan(root, fetcher, now=_ramp_time(now), source_ids=remaining)
            except (RegistryError, SourceFetchError, OSError) as error:
                ramp_error = f"{type(error).__name__}: {error}"
                stop_reasons.append("ramp source failure")
    reports = [report for report in (canary, ramp_report) if report is not None]
    report = {
        "schema_version": 1,
        "campaign_id": policy["campaign_id"],
        "planned_capacity_range": policy["planned_capacity_range"],
        "registered_endpoints": len(selected),
        "canary_endpoints": len(canary_ids),
        "ramped": ramp_report is not None,
        "status": "continued" if ramp_report is not None else "checkpoint",
        "stop_reasons": stop_reasons,
        "metrics": {
            "source_requests": sum(item["metrics"]["sources_selected"] for item in reports),
            "observations": sum(item["metrics"]["observations_seen"] for item in reports),
            "downloaded_bytes": sum(item["metrics"]["downloaded_bytes"] for item in reports),
            "discoveries": sum(item["discoveries"] for item in reports),
            "normalized_candidates": sum(
                item["metrics"]["candidates_enqueued"] for item in reports
            ),
            "deep_reviews": 0,
            "usage_credits": {"measured": False},
        },
        "runs": reports,
    }
    if ramp_error is not None:
        report["ramp_error"] = ramp_error
    atomic_write_text(
        root / "runs" / f"{now.replace(':', '-')}-campaign.json",
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return report
