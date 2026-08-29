from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .io import load_json
from .runtime_store import open_runtime_store
from .scaling import load_scale_policy
from .sources import load_registry


class ReportingError(ValueError):
    pass


REVIEW_PRIORITY = {
    "official": (0, "high"),
    "representative": (1, "normal"),
    "discovery": (2, "low"),
}

QUEUE_PRIORITY = {
    "urgent-impact": 0,
    "official-gap": 1,
    "reactivation": 2,
    "novel-discovery": 3,
    "aged-backlog": 4,
}


def _outcome_name(value: object) -> object:
    return "not_promoted" if value == "discard" else value


def repository_status(root: Path) -> dict[str, Any]:
    sources = load_registry(root)
    catalog = load_json(root / "catalog" / "capabilities.json")
    marketplace = load_json(root / ".agents" / "plugins" / "marketplace.json")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("internal"), list):
        raise ReportingError("capability catalog is invalid")
    if not isinstance(marketplace, dict) or not isinstance(marketplace.get("plugins"), list):
        raise ReportingError("plugin marketplace is invalid")

    with open_runtime_store(root) as store:
        candidates = list(store.discoveries())
        source_states = store.source_state_count()
        last_successful_run = store.last_successful_run()
        records = list(store.decisions())
    candidate_statuses = Counter(candidate.get("review_status") for candidate in candidates)
    pending_by_source = Counter(
        candidate["source_id"]
        for candidate in candidates
        if candidate.get("review_status") == "pending"
    )

    decision_outcomes = Counter(_outcome_name(record.get("outcome")) for record in records)

    return {
        "schema_version": 1,
        "last_successful_run": last_successful_run,
        "sources": {
            "registered": len(sources),
            "with_state": source_states,
        },
        "candidates": {
            "total": len(candidates),
            "pending": candidate_statuses["pending"],
            "applied": candidate_statuses["applied"],
        },
        "pending_by_source": dict(sorted(pending_by_source.items())),
        "decision_outcomes": dict(sorted(decision_outcomes.items())),
        "catalog": {
            "plugins": len(marketplace["plugins"]),
            "skills": len(catalog["internal"]),
            "internal_capabilities": len(catalog["internal"]),
            "external_capabilities": len(catalog.get("external", [])),
        },
    }


def _queue_item(candidate: dict[str, Any], queue_name: str) -> dict[str, Any]:
    license_value = candidate.get("license")
    if not isinstance(license_value, dict):
        raise ReportingError("candidate license is invalid")
    trust = candidate.get("trust")
    if trust not in REVIEW_PRIORITY:
        raise ReportingError("candidate trust is invalid")
    if queue_name not in QUEUE_PRIORITY:
        raise ReportingError("candidate queue is invalid")
    return {
        "id": candidate.get("id"),
        "source_id": candidate.get("source_id"),
        "title": candidate.get("title"),
        "trust": trust,
        "priority": REVIEW_PRIORITY[trust][1],
        "queue": queue_name,
        "license_status": license_value.get("status"),
        "canonical_url": candidate.get("canonical_url"),
        "observed_at": candidate.get("observed_at"),
    }


def _queue_sort_key(item: dict[str, Any]) -> tuple[int, int, str, str]:
    return (
        QUEUE_PRIORITY[item["queue"]],
        REVIEW_PRIORITY[item["trust"]][0],
        str(item["observed_at"]),
        str(item["id"]),
    )


def review_queue(
    root: Path,
    source_id: str | None = None,
    *,
    limit: int | None = None,
    after: str | None = None,
) -> dict[str, Any]:
    review_batch = load_scale_policy(root)["review_batch"]
    selected_limit = review_batch["default"] if limit is None else limit
    maximum_limit = review_batch["maximum"]
    source_ids = {source["id"] for source in load_registry(root)}
    if source_id is not None and source_id not in source_ids:
        raise ReportingError(f"unknown source id: {source_id}")
    if (
        not isinstance(selected_limit, int)
        or isinstance(selected_limit, bool)
        or not 1 <= selected_limit <= maximum_limit
    ):
        raise ReportingError(
            f"review limit must be between 1 and {maximum_limit}"
        )

    items: list[dict[str, Any]] = []
    cursor_item: dict[str, Any] | None = None
    with open_runtime_store(root) as store:
        entries = list(store.queue_entries())
    for candidate, queue_name in entries:
        if candidate.get("id") == after:
            if source_id is not None and candidate.get("source_id") != source_id:
                raise ReportingError("review cursor is outside the selected source")
            cursor_item = _queue_item(candidate, queue_name)
        if source_id is not None and candidate.get("source_id") != source_id:
            continue
        items.append(_queue_item(candidate, queue_name))
    if after is not None and cursor_item is None:
        raise ReportingError(f"unknown review cursor: {after}")

    items.sort(key=_queue_sort_key)
    pending = len(items)
    by_source = Counter(str(item["source_id"]) for item in items)
    if cursor_item is not None:
        cursor_key = _queue_sort_key(cursor_item)
        items = [item for item in items if _queue_sort_key(item) > cursor_key]
    page = items[:selected_limit]
    next_cursor = page[-1]["id"] if len(items) > len(page) else None
    return {
        "schema_version": 1,
        "pending": pending,
        "returned": len(page),
        "limit": selected_limit,
        "next_cursor": next_cursor,
        "by_source": dict(sorted(by_source.items())),
        "items": page,
    }


def _line(value: Any) -> str:
    return " ".join("".join(character for character in str(value) if character.isprintable()).split())


def render_status(report: dict[str, Any]) -> str:
    lines = [
        f"last_successful_run={report['last_successful_run']}",
        (
            f"sources={report['sources']['registered']} "
            f"state_sources={report['sources']['with_state']} "
            f"pending={report['candidates']['pending']} "
            f"applied={report['candidates']['applied']} "
            f"plugins={report['catalog']['plugins']} "
            f"skills={report['catalog']['skills']}"
        ),
    ]
    for source_id, count in report["pending_by_source"].items():
        lines.append(f"pending_source={source_id} count={count}")
    for outcome, count in report["decision_outcomes"].items():
        lines.append(f"decision={outcome} count={count}")
    return "\n".join(lines)


def render_review_queue(report: dict[str, Any]) -> str:
    lines = [
        (
            f"pending={report['pending']} returned={report['returned']} "
            f"limit={report['limit']} next_cursor={report['next_cursor']}"
        )
    ]
    for source_id, count in report["by_source"].items():
        lines.append(f"source={source_id} count={count}")
    for item in report["items"]:
        lines.append(
            " ".join(
                (
                    f"id={_line(item['id'])}",
                    f"source={_line(item['source_id'])}",
                    f"priority={_line(item['priority'])}",
                    f"queue={_line(item['queue'])}",
                    f"trust={_line(item['trust'])}",
                    f"license={_line(item['license_status'])}",
                    f"title={_line(item['title'])}",
                )
            )
        )
    return "\n".join(lines)
