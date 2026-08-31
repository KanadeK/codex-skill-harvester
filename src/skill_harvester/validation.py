from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .decisions import bundle_hash, normalize_fingerprint
from .campaign import (
    CampaignPolicyError,
    campaign_source_context,
    load_campaign_policy,
)
from .io import load_json
from .production import ProductionReportError, build_production_report
from .queries import QueryBatchError, load_topic_bank
from .scaling import (
    ScalePolicyError,
    evaluate_migration_triggers,
    inventory_repository,
    load_scale_policy,
)
from .runtime_store import RuntimeStoreError, open_runtime_store
from .sources import load_registry
from .taxonomy import TaxonomyError, validate_catalog_taxonomy


class ValidationError(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _relative_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    _require(path.is_relative_to(root.resolve()), f"path escapes repository: {value}")
    return path


def _skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    _require(text.startswith("---\n"), f"Skill frontmatter missing: {path}")
    end = text.find("\n---\n", 4)
    _require(end != -1, f"Skill frontmatter is not closed: {path}")
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_-]+):\s*(.+)", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip("\"'")
    return fields


def _scan_secrets(root: Path) -> list[str]:
    patterns = (
        re.compile("-----BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
        re.compile("sk-" + r"(?:proj-)?[A-Za-z0-9_-]{32,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
    )
    excluded = {".git", "dist", "build", ".venv", "__pycache__", ".harvester-cache"}
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in excluded for part in path.relative_to(root).parts):
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8")
        if any(pattern.search(text) for pattern in patterns):
            findings.append(path.relative_to(root).as_posix())
    return findings


def _validate_unmeasured(value: Any, label: str) -> None:
    _require(value == {"measured": False}, f"{label} must be measured=false")


def _nonnegative_integer(value: Any, label: str) -> None:
    _require(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0,
        f"{label} must be a non-negative integer",
    )


def _validate_query_report(root: Path, path: Path, report: dict[str, Any]) -> None:
    _require(report.get("schema_version") == 1, f"query schema invalid: {path.name}")
    _require(report.get("report_type") == "query-results", f"query type invalid: {path.name}")
    _require(
        isinstance(report.get("cycle_id"), str) and report["cycle_id"],
        f"query cycle invalid: {path.name}",
    )
    _require(report.get("status") in {"pending", "completed"}, f"query status invalid: {path.name}")
    for field in (
        "actual_queries",
        "completed_queries",
        "failed_queries",
        "pending_queries",
        "result_count",
        "selected_endpoints",
    ):
        _nonnegative_integer(report.get(field), f"query {field}: {path.name}")
    if "discovery_hits" in report:
        _nonnegative_integer(
            report["discovery_hits"], f"query discovery_hits: {path.name}"
        )
    if report.get("aggregation") == "cycle":
        _nonnegative_integer(
            report.get("query_attempts"), f"query query_attempts: {path.name}"
        )
        _require(
            report["actual_queries"] == report["completed_queries"]
            and report["query_attempts"]
            == report["completed_queries"] + report["failed_queries"],
            f"query cycle stage counts disagree: {path.name}",
        )
        review = report.get("discovery_review")
        _require(
            isinstance(review, dict),
            f"query discovery review missing: {path.name}",
        )
        for field in (
            "raw_hits",
            "unique_hits",
            "pending",
            "selected_endpoint",
            "duplicate",
            "not_selected",
            "reviewed",
        ):
            _nonnegative_integer(
                review.get(field), f"query discovery review {field}: {path.name}"
            )
        _require(
            review["raw_hits"] >= review["unique_hits"]
            and review["unique_hits"]
            == review["pending"]
            + review["selected_endpoint"]
            + review["duplicate"]
            + review["not_selected"]
            and review["reviewed"]
            == review["selected_endpoint"]
            + review["duplicate"]
            + review["not_selected"],
            f"query discovery review counts disagree: {path.name}",
        )
        expected_rate = (
            round(review["selected_endpoint"] / review["reviewed"], 6)
            if review["reviewed"]
            else 0.0
        )
        _require(
            review.get("conversion_rate") == expected_rate,
            f"query discovery review conversion disagrees: {path.name}",
        )
        with open_runtime_store(root) as store:
            expected_review = store.discovery_review_metrics(report["cycle_id"])
        _require(
            review == expected_review,
            f"query discovery review differs from SQLite: {path.name}",
        )
    else:
        _require(
            report["actual_queries"]
            == report["completed_queries"] + report["failed_queries"],
            f"query stage counts disagree: {path.name}",
        )
    selected_source_ids = report.get("selected_source_ids")
    _require(
        isinstance(selected_source_ids, list)
        and all(isinstance(source_id, str) and source_id for source_id in selected_source_ids)
        and len(selected_source_ids) == len(set(selected_source_ids))
        and report["selected_endpoints"] == len(selected_source_ids),
        f"query selected endpoints disagree: {path.name}",
    )
    _require(
        (report["status"] == "pending") == (report["pending_queries"] > 0),
        f"query checkpoint status disagrees: {path.name}",
    )


def _validate_semantic_report(
    root: Path,
    path: Path,
    report: dict[str, Any],
    *,
    validate_latest_checkpoint: bool,
) -> None:
    _require(report.get("schema_version") == 1, f"semantic schema invalid: {path.name}")
    _require(report.get("report_type") == "semantic-review", f"semantic type invalid: {path.name}")
    _require(
        isinstance(report.get("batch_id"), str) and report["batch_id"],
        f"semantic batch id invalid: {path.name}",
    )
    _require(
        isinstance(report.get("reviewed_at"), str) and report["reviewed_at"],
        f"semantic reviewed_at invalid: {path.name}",
    )
    _require(report.get("status") in {"pending", "completed"}, f"semantic status invalid: {path.name}")
    for field in (
        "reviewed_observations",
        "pending_observations",
        "evidence_packs",
        "not_promoted",
        "normalized_candidates",
        "l2_matches",
        "l3_recalls",
    ):
        _nonnegative_integer(report.get(field), f"semantic {field}: {path.name}")
    _validate_unmeasured(report.get("deep_reviews"), f"semantic deep_reviews: {path.name}")
    _validate_unmeasured(report.get("usage_credits"), f"semantic usage_credits: {path.name}")
    try:
        with open_runtime_store(root) as store:
            batch = store.semantic_batch(report["batch_id"])
            batch_items = store.semantic_batch_items(report["batch_id"])
            packs = [
                pack
                for pack in store.evidence_packs_for_batch(report["batch_id"])
                if pack["reviewed_at"] == report["reviewed_at"]
            ]
            candidates = store.candidates_for_evidence_packs(
                {pack["id"] for pack in packs}
            )
    except RuntimeStoreError as error:
        raise ValidationError(str(error)) from error
    expected = {
        "reviewed_observations": sum(len(pack["observation_ids"]) for pack in packs),
        "evidence_packs": len(packs),
        "not_promoted": sum(pack["outcome"] == "not_promoted" for pack in packs),
        "normalized_candidates": len(candidates),
        "l2_matches": sum(len(candidate["l2_matches"]) for candidate in candidates),
        "l3_recalls": sum(len(candidate["l3_recall"]) for candidate in candidates),
    }
    for field, value in expected.items():
        _require(
            report[field] == value,
            f"semantic {field} does not match SQLite authority: {path.name}",
        )
    if validate_latest_checkpoint:
        _require(
            batch["status"] == report["status"],
            f"semantic batch status does not match SQLite authority: {path.name}",
        )
        _require(
            report["pending_observations"]
            == sum(item["status"] == "pending" for item in batch_items),
            f"semantic pending count does not match SQLite authority: {path.name}",
        )


def _validate_campaign_report(
    path: Path,
    report: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
    source_context: dict[str, dict[str, str]],
) -> None:
    _require(report.get("schema_version") == 2, f"campaign schema invalid: {path.name}")
    _require(report.get("report_type") == "campaign", f"campaign type invalid: {path.name}")
    _require(report.get("status") in {"changed", "no_op", "checkpoint"}, f"campaign status invalid: {path.name}")
    metrics = report.get("metrics")
    _require(isinstance(metrics, dict), f"campaign metrics missing: {path.name}")
    integer_metrics = (
        "source_requests",
        "source_successes",
        "failures",
        "raw_observations",
        "observations_inserted",
        "observation_duplicates",
        "normalized_candidates",
        "candidate_duplicates",
        "pending_queue",
        "l3_recalls",
        "downloaded_bytes",
        "runtime_store_bytes",
    )
    for field in integer_metrics:
        _require(
            isinstance(metrics.get(field), int)
            and not isinstance(metrics[field], bool)
            and metrics[field] >= 0,
            f"campaign metric {field} invalid: {path.name}",
        )
    _require(
        isinstance(metrics.get("source_success_rate"), (int, float))
        and not isinstance(metrics["source_success_rate"], bool)
        and 0 <= metrics["source_success_rate"] <= 1,
        f"campaign source_success_rate invalid: {path.name}",
    )
    _validate_unmeasured(metrics.get("deep_reviews"), f"campaign deep_reviews: {path.name}")
    _validate_unmeasured(metrics.get("usage_credits"), f"campaign usage_credits: {path.name}")

    stop_reasons = report.get("stop_reasons")
    _require(
        isinstance(stop_reasons, list)
        and all(isinstance(reason, str) and reason for reason in stop_reasons),
        f"campaign stop reasons invalid: {path.name}",
    )
    checkpoint = report.get("checkpoint")
    _require(isinstance(checkpoint, dict), f"campaign checkpoint missing: {path.name}")
    completed = checkpoint.get("completed_source_ids")
    pending = checkpoint.get("pending_source_ids")
    _require(
        isinstance(completed, list)
        and isinstance(pending, list)
        and all(isinstance(source_id, str) for source_id in completed + pending)
        and len(completed) == len(set(completed))
        and len(pending) == len(set(pending))
        and not (set(completed) & set(pending)),
        f"campaign checkpoint source ids invalid: {path.name}",
    )

    runs = report.get("runs")
    _require(isinstance(runs, list), f"campaign runs invalid: {path.name}")
    recomputed = {
        field: 0
        for field in (
            "raw_observations",
            "observations_inserted",
            "observation_duplicates",
            "normalized_candidates",
            "candidate_duplicates",
            "l3_recalls",
        )
    }
    completed_from_runs: list[str] = []
    for run in runs:
        _require(
            isinstance(run, dict)
            and run.get("schema_version") == 2
            and run.get("report_type") == "scan",
            f"campaign contains an invalid scan run: {path.name}",
        )
        _require(
            run.get("campaign_phase") in {"canary", "ramp"},
            f"campaign scan phase invalid: {path.name}",
        )
        run_metrics = run.get("metrics")
        _require(isinstance(run_metrics, dict), f"campaign scan metrics invalid: {path.name}")
        _validate_unmeasured(
            run_metrics.get("deep_reviews"), f"scan deep_reviews: {path.name}"
        )
        for field in recomputed:
            value = run_metrics.get(field)
            _require(
                isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"campaign scan metric {field} invalid: {path.name}",
            )
            recomputed[field] += value
        run_sources = run.get("sources")
        _require(
            isinstance(run_sources, list) and len(run_sources) == 1,
            f"campaign scan must contain one source checkpoint: {path.name}",
        )
        for source in run_sources:
            source_id = source.get("source_id")
            _require(
                source_id in source_by_id and source_id in source_context,
                f"campaign source unknown: {path.name}",
            )
            _require(
                {
                    "source_group": source.get("source_group"),
                    "topic_id": source.get("topic_id"),
                }
                == source_context[source_id],
                f"campaign source context drift: {path.name}",
            )
            completed_from_runs.append(source_id)
    _require(
        completed == completed_from_runs,
        f"campaign checkpoint does not match generated runs: {path.name}",
    )
    for field, expected in recomputed.items():
        _require(
            metrics[field] == expected,
            f"campaign metric {field} does not match generated runs: {path.name}",
        )
    _require(
        metrics["source_successes"] == len(runs),
        f"campaign source_successes does not match generated runs: {path.name}",
    )
    _require(
        metrics["source_requests"] >= len(runs),
        f"campaign source_requests is below generated runs: {path.name}",
    )


def validate_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    for name in (
        "AGENTS.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
        "SECURITY.md",
        "pyproject.toml",
        "catalog/taxonomy.json",
        "config/scale-policy.json",
        "config/campaign-policy.json",
        "config/topic-bank.json",
        "state/harvest.sqlite3",
        "docs/architecture.md",
        "docs/roadmap.md",
        "docs/scale-audit.md",
        "docs/schema-migrations.md",
        "docs/taxonomy.md",
        "scripts/benchmark_storage.py",
        "sources/registry.json",
        ".github/dependabot.yml",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/pull_request_template.md",
        ".github/workflows/ci.yml",
        ".github/workflows/harvest.yml",
    ):
        _require((root / name).is_file(), f"required repository file is missing: {name}")
    for legacy_path in (
        "state/harvest-state.json",
        "candidates/inbox",
        "decisions/records",
    ):
        _require(
            not (root / legacy_path).exists(),
            f"legacy runtime authority still exists: {legacy_path}",
        )

    harvest_workflow = (root / ".github" / "workflows" / "harvest.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "workflow_dispatch:",
        "schedule:",
        "actions: write",
        "contents: write",
        "pull-requests: write",
        "python -m skill_harvester campaign --root . --ramp",
        "git add -- state/harvest.sqlite3 runs",
        'gh workflow run ci.yml --ref "$branch"',
    ):
        _require(marker in harvest_workflow, f"harvest workflow contract missing: {marker}")
    _require(
        "skill_harvester apply" not in harvest_workflow,
        "harvest workflow must not apply semantic decisions",
    )
    ci_workflow = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    _require("workflow_dispatch:" in ci_workflow, "CI workflow must support explicit dispatch")
    _require(
        "python scripts/benchmark_storage.py --root . --records 100" in ci_workflow,
        "CI workflow must exercise the storage benchmark",
    )

    sources = load_registry(root)
    source_by_id = {source["id"]: source for source in sources}
    try:
        campaign_policy = load_campaign_policy(root)
    except CampaignPolicyError as error:
        raise ValidationError(str(error)) from error
    campaign_source_ids = {
        source_id
        for group in campaign_policy["source_groups"].values()
        for source_id in group["source_ids"]
    }
    _require(
        campaign_source_ids <= set(source_by_id),
        "campaign policy references unknown source",
    )
    campaign_context = campaign_source_context(campaign_policy)
    try:
        topic_queries = load_topic_bank(root)
    except QueryBatchError as error:
        raise ValidationError(str(error)) from error
    topic_ids = {query["topic_id"] for query in topic_queries}
    try:
        with open_runtime_store(root) as store:
            last_successful_run = store.last_successful_run()
            state_sources = dict(store.source_states())
            observations = list(store.observations())
            candidates = list(store.candidates())
            records = list(store.decisions())
            evidence_packs = list(store.evidence_packs())
    except RuntimeStoreError as error:
        raise ValidationError(str(error)) from error
    _require(isinstance(last_successful_run, str), "runtime store has no successful cursor")
    for source_id, cursor in state_sources.items():
        _require(source_id in source_by_id, f"state references unknown source: {source_id}")
        source = source_by_id[source_id]
        _require(cursor["url"] == source["url"], f"state URL drift: {source_id}")
        _require(cursor["adapter"] == source["adapter"], f"state adapter drift: {source_id}")
        _require(bool(re.fullmatch(r"[0-9a-f]{64}", cursor["content_sha256"])), f"state hash invalid: {source_id}")
        _require(isinstance(cursor["seen_items"], dict), f"state seen_items invalid: {source_id}")
        _require(
            isinstance(cursor.get("material_items", {}), dict),
            f"state material_items invalid: {source_id}",
        )
        _require(
            isinstance(cursor.get("window_item_ids", []), list),
            f"state window_item_ids invalid: {source_id}",
        )

    try:
        scale_policy = load_scale_policy(root)
        inventory = inventory_repository(root)
        migration_triggers = evaluate_migration_triggers(inventory, scale_policy)
    except ScalePolicyError as error:
        raise ValidationError(str(error)) from error

    catalog = load_json(root / "catalog" / "capabilities.json")
    taxonomy = load_json(root / "catalog" / "taxonomy.json")
    try:
        taxonomy_report = validate_catalog_taxonomy(catalog, taxonomy)
    except TaxonomyError as error:
        raise ValidationError(str(error)) from error
    internal = catalog.get("internal")
    external = catalog.get("external")
    _require(isinstance(internal, list) and isinstance(external, list), "catalog lists missing")
    marketplace = load_json(root / ".agents" / "plugins" / "marketplace.json")
    _require(marketplace.get("name") == "codex-skill-harvester", "marketplace identity invalid")
    marketplace_plugins = {entry["name"]: entry for entry in marketplace["plugins"]}

    skill_count = 0
    for entry in internal:
        normalize_fingerprint(entry["fingerprint"])
        plugin_id = entry["plugin_id"]
        skill_name = entry["skill_name"]
        plugin_root = root / "plugins" / plugin_id
        manifest = load_json(plugin_root / ".codex-plugin" / "plugin.json")
        _require(manifest["name"] == plugin_id and manifest["skills"] == "./skills/", f"plugin manifest invalid: {plugin_id}")
        skill_root = plugin_root / "skills" / skill_name
        fields = _skill_frontmatter(skill_root / "SKILL.md")
        _require(fields.get("name") == skill_name and bool(fields.get("description")), f"Skill identity invalid: {entry['id']}")
        files = {
            name: (skill_root / Path(name)).read_text(encoding="utf-8")
            for name in entry["managed_files"]
        }
        actual_hash = bundle_hash({"files": files})
        _require(actual_hash == entry["artifact_sha256"], f"artifact hash drift: {entry['id']}")
        _require(set(entry["source_refs"]) <= set(source_by_id), f"unknown capability source: {entry['id']}")
        market_entry = marketplace_plugins.get(plugin_id)
        _require(market_entry is not None, f"plugin absent from marketplace: {plugin_id}")
        _require(
            _relative_path(root, market_entry["source"]["path"]) == plugin_root,
            f"marketplace plugin path drift: {plugin_id}",
        )
        skill_count += 1

    for entry in external:
        normalize_fingerprint(entry["fingerprint"])
        _require(entry["source_ref"] in source_by_id, f"unknown external source: {entry['id']}")
        _require(bool(re.fullmatch(r"[0-9a-f]{64}", entry["artifact_sha256"])), f"external hash invalid: {entry['id']}")

    observations_by_id: dict[str, dict[str, Any]] = {}
    for observation in observations:
        observation_id = observation.get("id")
        _require(isinstance(observation_id, str), "runtime observation id invalid")
        _require(
            observation["source_id"] in source_by_id,
            f"observation source unknown: {observation_id}",
        )
        _require(
            isinstance(observation.get("source_group"), str)
            and observation["source_group"],
            f"observation source group invalid: {observation_id}",
        )
        _require(
            isinstance(observation.get("topic_id"), str) and observation["topic_id"],
            f"observation topic invalid: {observation_id}",
        )
        if observation["source_group"] != "legacy-import":
            _require(
                observation.get("tier") == source_by_id[observation["source_id"]]["tier"],
                f"observation tier drift: {observation_id}",
            )
            _require(
                observation["topic_id"] in topic_ids,
                f"observation topic is absent from Topic Bank: {observation_id}",
            )
        _require(
            not ({"raw_body", "body", "content", "instructions"} & set(observation)),
            f"raw source content persisted: {observation_id}",
        )
        observations_by_id[observation_id] = observation

    known_observation_ids = set(observations_by_id)
    known_source_ids = set(source_by_id)
    evidence_packs_by_id: dict[str, dict[str, Any]] = {}
    for pack in evidence_packs:
        pack_id = pack.get("id")
        _require(
            isinstance(pack_id, str) and pack_id not in evidence_packs_by_id,
            "Evidence Pack id is missing or duplicated",
        )
        _require(
            pack.get("schema_version") == 1
            and pack.get("outcome") in {"candidate", "not_promoted"}
            and pack.get("reviewed_by") == "codex",
            f"Evidence Pack authority invalid: {pack_id}",
        )
        observation_ids = pack.get("observation_ids")
        source_ids = pack.get("source_ids")
        _require(
            isinstance(observation_ids, list)
            and bool(observation_ids)
            and all(isinstance(observation_id, str) for observation_id in observation_ids)
            and len(observation_ids) == len(set(observation_ids))
            and set(observation_ids) <= known_observation_ids,
            f"Evidence Pack observations invalid: {pack_id}",
        )
        _require(
            isinstance(source_ids, list)
            and bool(source_ids)
            and all(isinstance(source_id, str) for source_id in source_ids)
            and set(source_ids) <= known_source_ids,
            f"Evidence Pack sources invalid: {pack_id}",
        )
        for field in ("necessary_facts", "non_obvious_decisions", "adjacent_capabilities"):
            value = pack.get(field)
            _require(
                isinstance(value, list)
                and all(isinstance(item, str) and item for item in value),
                f"Evidence Pack {field} invalid: {pack_id}",
            )
        _require(
            isinstance(pack.get("license_assessment"), str)
            and bool(pack["license_assessment"])
            and isinstance(pack.get("rationale"), str)
            and bool(pack["rationale"]),
            f"Evidence Pack rationale invalid: {pack_id}",
        )
        risk = pack.get("risk")
        _require(
            isinstance(risk, dict)
            and risk.get("level") in {"standard", "high"}
            and isinstance(risk.get("domains"), list),
            f"Evidence Pack risk invalid: {pack_id}",
        )
        if pack["outcome"] == "not_promoted":
            conditions = pack.get("reactivation_conditions")
            _require(
                isinstance(conditions, list)
                and bool(conditions)
                and all(isinstance(condition, str) and condition for condition in conditions),
                f"Evidence Pack reactivation conditions invalid: {pack_id}",
            )
        evidence_packs_by_id[pack_id] = pack

    candidate_count = 0
    applied_count = 0
    decisions_by_candidate = {record.get("candidate_id"): record for record in records}
    for candidate in candidates:
        candidate_id = candidate.get("id")
        _require(isinstance(candidate_id, str), "runtime candidate id invalid")
        _require(candidate["source_id"] in source_by_id, f"candidate source unknown: {candidate_id}")
        observation = observations_by_id.get(candidate.get("observation_id"))
        _require(observation is not None, f"candidate observation missing: {candidate_id}")
        _require(
            candidate.get("source_group") == observation["source_group"]
            and candidate.get("topic_id") == observation["topic_id"],
            f"candidate source context drift: {candidate_id}",
        )
        normalize_fingerprint(candidate.get("fingerprint"))
        _require(
            isinstance(candidate.get("l2_matches"), list)
            or candidate.get("source_group") == "legacy-import",
            f"candidate L2 evidence invalid: {candidate_id}",
        )
        _require(
            isinstance(candidate.get("l3_recall"), list),
            f"candidate L3 recall invalid: {candidate_id}",
        )
        evidence_pack_id = candidate.get("evidence_pack_id")
        _require(
            isinstance(evidence_pack_id, str) and evidence_pack_id,
            f"candidate Evidence Pack reference invalid: {candidate_id}",
        )
        evidence_pack = evidence_packs_by_id.get(evidence_pack_id)
        _require(
            evidence_pack is not None
            and evidence_pack.get("outcome") == "candidate"
            and candidate.get("observation_id")
            in evidence_pack.get("observation_ids", []),
            f"candidate Evidence Pack linkage invalid: {candidate_id}",
        )
        _require(candidate["review_status"] in {"pending", "applied"}, f"candidate status invalid: {candidate_id}")
        _require(not ({"raw_body", "body", "content", "instructions"} & set(candidate)), f"raw source content persisted: {candidate_id}")
        if candidate["review_status"] == "applied":
            record = decisions_by_candidate.get(candidate_id)
            _require(record is not None, f"decision record missing: {candidate_id}")
            _require(record["candidate_id"] == candidate_id, f"decision record mismatch: {candidate_id}")
            _require(record["outcome"] == candidate["decision_outcome"], f"decision outcome mismatch: {candidate_id}")
            _require(
                candidate.get("decision_record") == f"sqlite:decisions/{candidate_id}",
                f"decision reference invalid: {candidate_id}",
            )
            applied_count += 1
        candidate_count += 1

    _require(len(records) == applied_count, "applied candidate and decision record counts differ")
    for record in records:
        _require(
            record.get("schema_version") in {1, 2},
            "decision schema invalid",
        )
        _require(record["reviewed_by"] == "codex", "unreviewed decision record")
        _require(set(record["source_refs"]) <= set(source_by_id), "decision source unknown")
        if record.get("schema_version") == 2 and record.get("outcome") == "not_promoted":
            conditions = record.get("reactivation_conditions")
            _require(
                isinstance(conditions, list)
                and bool(conditions)
                and all(isinstance(condition, str) and condition for condition in conditions),
                "decision reactivation conditions invalid",
            )

    for path in (root / "runs").glob("*-campaign.json"):
        report = load_json(path)
        _require(isinstance(report, dict), f"campaign report invalid: {path.name}")
        _validate_campaign_report(path, report, source_by_id, campaign_context)

    for path in (root / "runs").glob("*-queries.json"):
        report = load_json(path)
        _require(isinstance(report, dict), f"query report invalid: {path.name}")
        _validate_query_report(root, path, report)

    semantic_reports: list[tuple[Path, dict[str, Any]]] = []
    latest_semantic_report: dict[str, tuple[str, Path]] = {}
    for path in sorted((root / "runs").glob("*-semantic.json")):
        report = load_json(path)
        _require(isinstance(report, dict), f"semantic report invalid: {path.name}")
        batch_id = report.get("batch_id")
        reviewed_at = report.get("reviewed_at")
        _require(
            isinstance(batch_id, str) and isinstance(reviewed_at, str),
            f"semantic checkpoint identity invalid: {path.name}",
        )
        previous = latest_semantic_report.get(batch_id)
        if previous is None or reviewed_at > previous[0]:
            latest_semantic_report[batch_id] = (reviewed_at, path)
        semantic_reports.append((path, report))
    for path, report in semantic_reports:
        _validate_semantic_report(
            root,
            path,
            report,
            validate_latest_checkpoint=(
                latest_semantic_report[report["batch_id"]][1] == path
            ),
        )

    for path in (root / "runs").glob("*-production.json"):
        report = load_json(path)
        _require(isinstance(report, dict), f"production report invalid: {path.name}")
        _require(
            report.get("schema_version") == 1
            and report.get("report_type") == "content-production",
            f"production report schema invalid: {path.name}",
        )
        try:
            expected = build_production_report(
                root,
                generated_at=report["generated_at"],
                campaign_report_path=_relative_path(
                    root, report["inputs"]["campaign_report"]
                ),
                query_report_paths=[
                    _relative_path(root, value)
                    for value in report["inputs"]["query_reports"]
                ],
                semantic_report_paths=[
                    _relative_path(root, value)
                    for value in report["inputs"]["semantic_reports"]
                ],
                supplemental_scan_paths=[
                    _relative_path(root, value)
                    for value in report["inputs"]["supplemental_scans"]
                ],
                query_no_op_report_path=_relative_path(
                    root, report["inputs"]["query_no_op_report"]
                ),
                semantic_no_op_report_path=_relative_path(
                    root, report["inputs"]["semantic_no_op_report"]
                ),
                stable_no_op_scan_path=_relative_path(
                    root, report["inputs"]["stable_no_op_scan"]
                ),
            )
        except (KeyError, ProductionReportError, RuntimeStoreError) as error:
            raise ValidationError(f"production report cannot be rebuilt: {path.name}: {error}") from error
        _require(
            report == expected,
            f"production report does not match authoritative inputs: {path.name}",
        )

    secret_files = _scan_secrets(root)
    _require(not secret_files, "secret-like material found: " + ", ".join(secret_files))
    return {
        "sources": len(sources),
        "state_sources": len(state_sources),
        "observations": len(observations),
        "candidates": candidate_count,
        "applied_candidates": applied_count,
        "decision_records": len(records),
        "evidence_packs": len(evidence_packs),
        "topic_queries": len(topic_queries),
        "plugins": len(marketplace_plugins),
        "skills": skill_count,
        "internal_capabilities": len(internal),
        "external_capabilities": len(external),
        "taxonomy_version": taxonomy_report["taxonomy_version"],
        "scale_backend": scale_policy["backend"],
        "migration_triggers": migration_triggers,
        "secrets_found": 0,
    }
