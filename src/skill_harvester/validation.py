from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .decisions import bundle_hash, normalize_fingerprint
from .io import load_json
from .sources import load_registry


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


def validate_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    for name in (
        "AGENTS.md",
        "CODE_OF_CONDUCT.md",
        "LICENSE",
        "SECURITY.md",
        "pyproject.toml",
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

    harvest_workflow = (root / ".github" / "workflows" / "harvest.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "workflow_dispatch:",
        "schedule:",
        "contents: write",
        "pull-requests: write",
        "python -m skill_harvester scan --root .",
        "git add -- state/harvest-state.json candidates/inbox runs",
    ):
        _require(marker in harvest_workflow, f"harvest workflow contract missing: {marker}")
    _require(
        "skill_harvester apply" not in harvest_workflow,
        "harvest workflow must not apply semantic decisions",
    )

    sources = load_registry(root)
    source_by_id = {source["id"]: source for source in sources}
    state = load_json(root / "state" / "harvest-state.json")
    _require(isinstance(state, dict) and state.get("schema_version") == 1, "state schema invalid")
    _require(isinstance(state.get("last_successful_run"), str), "state has no successful cursor")
    state_sources = state.get("sources")
    _require(isinstance(state_sources, dict), "state sources must be an object")
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

    catalog = load_json(root / "catalog" / "capabilities.json")
    _require(isinstance(catalog, dict) and catalog.get("schema_version") == 1, "catalog schema invalid")
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
        _require(entry["id"] == f"{plugin_id}:{skill_name}", f"capability id drift: {entry['id']}")
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

    candidate_count = 0
    applied_count = 0
    for path in sorted((root / "candidates" / "inbox").glob("*.json")):
        candidate = load_json(path)
        _require(candidate["id"] == path.stem, f"candidate filename drift: {path.name}")
        _require(candidate["source_id"] in source_by_id, f"candidate source unknown: {path.name}")
        _require(candidate["review_status"] in {"pending", "applied"}, f"candidate status invalid: {path.name}")
        _require(not ({"raw_body", "body", "content", "instructions"} & set(candidate)), f"raw source content persisted: {path.name}")
        if candidate["review_status"] == "applied":
            record_path = _relative_path(root, candidate["decision_record"])
            record = load_json(record_path)
            _require(record["candidate_id"] == candidate["id"], f"decision record mismatch: {path.name}")
            _require(record["outcome"] == candidate["decision_outcome"], f"decision outcome mismatch: {path.name}")
            applied_count += 1
        candidate_count += 1

    records = list((root / "decisions" / "records").glob("*.json"))
    _require(len(records) == applied_count, "applied candidate and decision record counts differ")
    for path in records:
        record = load_json(path)
        _require(record["reviewed_by"] == "codex", f"unreviewed decision record: {path.name}")
        _require(set(record["source_refs"]) <= set(source_by_id), f"decision source unknown: {path.name}")

    for path in (root / "runs").glob("*.json"):
        report = load_json(path)
        _require(report.get("schema_version") == 1, f"run schema invalid: {path.name}")
        for source in report.get("sources", []):
            _require(source["source_id"] in source_by_id, f"run source unknown: {path.name}")

    secret_files = _scan_secrets(root)
    _require(not secret_files, "secret-like material found: " + ", ".join(secret_files))
    return {
        "sources": len(sources),
        "state_sources": len(state_sources),
        "candidates": candidate_count,
        "applied_candidates": applied_count,
        "decision_records": len(records),
        "plugins": len(marketplace_plugins),
        "skills": skill_count,
        "internal_capabilities": len(internal),
        "external_capabilities": len(external),
        "secrets_found": 0,
    }
