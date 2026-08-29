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
        with open_runtime_store(root) as store:
            last_successful_run = store.last_successful_run()
            state_sources = dict(store.source_states())
            observations = list(store.observations())
            candidates = list(store.candidates())
            records = list(store.decisions())
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
        _require(
            not ({"raw_body", "body", "content", "instructions"} & set(observation)),
            f"raw source content persisted: {observation_id}",
        )
        observations_by_id[observation_id] = observation

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

    secret_files = _scan_secrets(root)
    _require(not secret_files, "secret-like material found: " + ", ".join(secret_files))
    return {
        "sources": len(sources),
        "state_sources": len(state_sources),
        "observations": len(observations),
        "candidates": candidate_count,
        "applied_candidates": applied_count,
        "decision_records": len(records),
        "plugins": len(marketplace_plugins),
        "skills": skill_count,
        "internal_capabilities": len(internal),
        "external_capabilities": len(external),
        "taxonomy_version": taxonomy_report["taxonomy_version"],
        "scale_backend": scale_policy["backend"],
        "migration_triggers": migration_triggers,
        "secrets_found": 0,
    }
