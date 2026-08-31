from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import load_json
from .runtime_store import RuntimeStoreError, open_runtime_store
from .scaling import load_scale_policy
from .sources import load_registry


class ReportingError(ValueError):
    pass


REVIEW_PRIORITY = {
    "official": (0, "high"),
    "representative": (1, "normal"),
    "discovery": (2, "low"),
}

def repository_status(root: Path) -> dict[str, Any]:
    sources = load_registry(root)
    catalog = load_json(root / "catalog" / "capabilities.json")
    marketplace = load_json(root / ".agents" / "plugins" / "marketplace.json")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("internal"), list):
        raise ReportingError("capability catalog is invalid")
    if not isinstance(marketplace, dict) or not isinstance(marketplace.get("plugins"), list):
        raise ReportingError("plugin marketplace is invalid")

    with open_runtime_store(root) as store:
        observation_count = store.observation_count()
        candidate_count = store.candidate_count()
        candidate_statuses = store.candidate_status_counts()
        source_states = store.source_state_count()
        last_successful_run = store.last_successful_run()
        pending_by_source = store.pending_by_source()
        decision_outcomes = store.decision_outcome_counts()
        discovery_hits = store.discovery_review_metrics()

    return {
        "schema_version": 1,
        "last_successful_run": last_successful_run,
        "sources": {
            "registered": len(sources),
            "with_state": source_states,
        },
        "observations": {"total": observation_count},
        "candidates": {
            "total": candidate_count,
            "pending": candidate_statuses.get("pending", 0),
            "applied": candidate_statuses.get("applied", 0),
        },
        "pending_by_source": pending_by_source,
        "decision_outcomes": decision_outcomes,
        "discovery_hits": discovery_hits,
        "catalog": {
            "plugins": len(marketplace["plugins"]),
            "skills": len(catalog["internal"]),
            "internal_capabilities": len(catalog["internal"]),
            "external_capabilities": len(catalog.get("external", [])),
        },
    }


def _queue_item(candidate: dict[str, Any]) -> dict[str, Any]:
    license_value = candidate.get("license")
    if not isinstance(license_value, dict):
        raise ReportingError("candidate license is invalid")
    trust = candidate.get("trust")
    if trust not in REVIEW_PRIORITY:
        raise ReportingError("candidate trust is invalid")
    queue_name = candidate.get("queue")
    if not isinstance(queue_name, str):
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

    try:
        with open_runtime_store(root) as store:
            page = store.review_page(
                source_id=source_id, limit=selected_limit, after=after
            )
    except RuntimeStoreError as error:
        raise ReportingError(str(error)) from error
    items = [_queue_item(candidate) for candidate in page["records"]]
    return {
        "schema_version": 1,
        "pending": page["pending"],
        "returned": len(items),
        "limit": selected_limit,
        "next_cursor": page["next_cursor"],
        "by_source": page["by_source"],
        "items": items,
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
            f"pending_discovery={report['discovery_hits']['pending']} "
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
