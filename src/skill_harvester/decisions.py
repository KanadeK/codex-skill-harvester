from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from .io import atomic_write_json, atomic_write_text, canonical_json_bytes, load_json, sha256_bytes
from .sources import load_registry
from .taxonomy import TaxonomyError, validate_catalog_taxonomy, validate_classification


FINGERPRINT_FIELDS = (
    "goal",
    "triggers",
    "inputs",
    "outputs",
    "tools",
    "side_effects",
    "platforms",
)


class DecisionError(ValueError):
    pass


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def normalize_fingerprint(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionError("fingerprint must be an object")
    normalized: dict[str, Any] = {}
    for field in FINGERPRINT_FIELDS:
        field_value = value.get(field)
        if field == "goal":
            if not isinstance(field_value, str) or not field_value.strip():
                raise DecisionError("fingerprint goal must be a non-empty string")
            normalized[field] = _normalized_text(field_value)
            continue
        if not isinstance(field_value, list) or not field_value:
            raise DecisionError(f"fingerprint {field} must be a non-empty list")
        if any(not isinstance(item, str) or not item.strip() for item in field_value):
            raise DecisionError(f"fingerprint {field} values must be non-empty strings")
        normalized[field] = sorted({_normalized_text(item) for item in field_value})
    return normalized


def bundle_hash(artifact: Any) -> str:
    if not isinstance(artifact, dict) or not isinstance(artifact.get("files"), dict):
        raise DecisionError("artifact must contain a files object")
    files = artifact["files"]
    if not files or any(not isinstance(path, str) or not isinstance(text, str) for path, text in files.items()):
        raise DecisionError("artifact files must map paths to text")
    return sha256_bytes(canonical_json_bytes(files))


def _catalog_entries(catalog: Any) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or catalog.get("schema_version") not in {1, 2}:
        raise DecisionError("catalog must use schema_version 1 or 2")
    internal = catalog.get("internal")
    external = catalog.get("external")
    if not isinstance(internal, list) or not isinstance(external, list):
        raise DecisionError("catalog must contain internal and external lists")
    entries = internal + external
    if any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str) for entry in entries):
        raise DecisionError("catalog entries must have string ids")
    return entries


def recommend_decision(candidate: Any, catalog: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict) or not isinstance(candidate.get("candidate_id"), str):
        raise DecisionError("candidate must have a string candidate_id")
    entries = _catalog_entries(catalog)
    artifact_sha256 = bundle_hash(candidate["artifact"]) if candidate.get("artifact") else None
    if artifact_sha256:
        exact = sorted(
            entry["id"] for entry in entries if entry.get("artifact_sha256") == artifact_sha256
        )
        if exact:
            return {
                "outcome": "discard_exact",
                "matches": exact,
                "artifact_sha256": artifact_sha256,
            }

    target = candidate.get("proposed_target_capability_id")
    if target is not None:
        if not isinstance(target, str) or target not in {
            entry["id"] for entry in catalog["internal"]
        }:
            raise DecisionError("proposed update target must name an internal capability")
        return {
            "outcome": "update_existing",
            "matches": [target],
            "artifact_sha256": artifact_sha256,
        }

    fingerprint = normalize_fingerprint(candidate.get("fingerprint"))
    semantic = sorted(
        entry["id"]
        for entry in entries
        if normalize_fingerprint(entry.get("fingerprint")) == fingerprint
    )
    if semantic:
        return {
            "outcome": "merge_semantic",
            "matches": semantic,
            "artifact_sha256": artifact_sha256,
        }
    return {"outcome": "create_new", "matches": [], "artifact_sha256": artifact_sha256}


def _kebab(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise DecisionError(f"{label} must use lower-case kebab-case")
    return value


def _artifact_files(artifact: dict[str, Any]) -> dict[str, str]:
    files = artifact.get("files")
    if not isinstance(files, dict) or "SKILL.md" not in files:
        raise DecisionError("artifact files must contain SKILL.md")
    total_bytes = 0
    validated: dict[str, str] = {}
    for name, content in files.items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise DecisionError("artifact files must map paths to text")
        if "\\" in name:
            raise DecisionError("artifact file paths must use forward slashes")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise DecisionError(f"artifact file path escapes the Skill: {name}")
        if path.parts[0] not in {"SKILL.md", "agents", "assets", "references", "scripts"}:
            raise DecisionError(f"artifact file path is outside supported Skill resources: {name}")
        encoded_size = len(content.encode("utf-8"))
        if encoded_size > 200_000:
            raise DecisionError(f"artifact file exceeds the 200000-byte limit: {name}")
        total_bytes += encoded_size
        validated[name] = content
    if total_bytes > 1_000_000:
        raise DecisionError("artifact bundle exceeds the 1000000-byte limit")
    return validated


def _validate_skill(skill_text: str, skill_name: str) -> None:
    normalized = skill_text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise DecisionError("SKILL.md must start with YAML frontmatter")
    end = normalized.find("\n---\n", 4)
    if end == -1:
        raise DecisionError("SKILL.md frontmatter is not closed")
    fields: dict[str, str] = {}
    for line in normalized[4:end].splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_-]+):\s*(.+)", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"\'')
    if fields.get("name") != skill_name:
        raise DecisionError("SKILL.md name must match the artifact skill_name")
    description = fields.get("description", "")
    if not description or len(description) > 1024:
        raise DecisionError("SKILL.md description must contain 1 to 1024 characters")
    if "[TODO:" in skill_text:
        raise DecisionError("SKILL.md contains an unfinished TODO placeholder")


def _validate_plugin_manifest(manifest: Any, plugin_id: str) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("name") != plugin_id:
        raise DecisionError("plugin manifest name must match plugin_id")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise DecisionError("plugin manifest version must use strict semver")
    if not isinstance(manifest.get("description"), str) or not manifest["description"].strip():
        raise DecisionError("plugin manifest needs a description")
    author = manifest.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str):
        raise DecisionError("plugin manifest needs author.name")
    if manifest.get("skills") != "./skills/":
        raise DecisionError("plugin manifest skills path must be ./skills/")
    interface = manifest.get("interface")
    required_interface = (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
    )
    if not isinstance(interface, dict) or any(field not in interface for field in required_interface):
        raise DecisionError("plugin manifest is missing required interface metadata")
    return manifest


def _validated_artifact(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionError("create and update decisions require an artifact")
    if value.get("origin") != "original-synthesis":
        raise DecisionError("artifact origin must be original-synthesis")
    plugin_id = _kebab(value.get("plugin_id"), "plugin_id")
    skill_name = _kebab(value.get("skill_name"), "skill_name")
    files = _artifact_files(value)
    _validate_skill(files["SKILL.md"], skill_name)
    manifest = _validate_plugin_manifest(value.get("plugin_manifest"), plugin_id)
    return {
        "origin": "original-synthesis",
        "plugin_id": plugin_id,
        "plugin_manifest": manifest,
        "skill_name": skill_name,
        "files": files,
    }


def _catalog(root: Path) -> dict[str, Any]:
    value = load_json(
        root / "catalog" / "capabilities.json",
        {"schema_version": 1, "internal": [], "external": []},
    )
    _catalog_entries(value)
    if value["schema_version"] == 2:
        _validate_catalog_for_decision(
            value, load_json(root / "catalog" / "taxonomy.json")
        )
    return value


def _validate_catalog_for_decision(
    catalog: dict[str, Any], taxonomy: dict[str, Any]
) -> None:
    try:
        validate_catalog_taxonomy(catalog, taxonomy)
    except TaxonomyError as error:
        raise DecisionError(str(error)) from error


def _validate_classification_for_decision(
    value: Any,
    taxonomy: dict[str, Any],
    capability_id: str,
) -> None:
    try:
        validate_classification(value, taxonomy, capability_id)
    except TaxonomyError as error:
        raise DecisionError(str(error)) from error


def _internal_entry(catalog: dict[str, Any], capability_id: str) -> dict[str, Any] | None:
    return next((entry for entry in catalog["internal"] if entry["id"] == capability_id), None)


def _marketplace_with_plugin(
    root: Path, plugin_id: str, manifest: dict[str, Any]
) -> dict[str, Any]:
    path = root / ".agents" / "plugins" / "marketplace.json"
    marketplace = load_json(
        path,
        {
            "name": "codex-skill-harvester",
            "interface": {"displayName": "Codex Skill Harvester"},
            "plugins": [],
        },
    )
    if not isinstance(marketplace, dict) or not isinstance(marketplace.get("plugins"), list):
        raise DecisionError("marketplace must contain a plugins list")
    entry = {
        "name": plugin_id,
        "source": {"source": "local", "path": f"./plugins/{plugin_id}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": manifest["interface"]["category"],
    }
    existing = next(
        (index for index, value in enumerate(marketplace["plugins"]) if value.get("name") == plugin_id),
        None,
    )
    if existing is None:
        marketplace["plugins"].append(entry)
    else:
        marketplace["plugins"][existing] = entry
    return marketplace


def _write_artifact(root: Path, artifact: dict[str, Any], previous: dict[str, Any] | None) -> None:
    plugin_root = root / "plugins" / artifact["plugin_id"]
    skill_root = plugin_root / "skills" / artifact["skill_name"]
    new_files = set(artifact["files"])
    if previous:
        for old_name in previous.get("managed_files", []):
            if old_name not in new_files:
                old_path = skill_root.joinpath(*PurePosixPath(old_name).parts)
                old_path.unlink(missing_ok=True)
    atomic_write_json(plugin_root / ".codex-plugin" / "plugin.json", artifact["plugin_manifest"])
    for name, content in artifact["files"].items():
        atomic_write_text(skill_root.joinpath(*PurePosixPath(name).parts), content)


def _validate_decision(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") not in {1, 2}:
        raise DecisionError("decision must use schema_version 1 or 2")
    schema_version = value["schema_version"]
    candidate_id = _kebab(value.get("candidate_id"), "candidate_id")
    if value.get("reviewed_by") != "codex":
        raise DecisionError("reviewed_by must be codex before publication")
    if not isinstance(value.get("reviewed_at"), str) or not value["reviewed_at"]:
        raise DecisionError("decision needs reviewed_at")
    outcomes = (
        {"discard", "merge", "update", "create"}
        if schema_version == 1
        else {"not_promoted", "merge", "update", "create"}
    )
    if value.get("outcome") not in outcomes:
        raise DecisionError(
            "schema 1 uses discard; schema 2 uses not_promoted; both support merge, update, and create"
        )
    if schema_version == 2 and value["outcome"] == "create":
        canonical_id = value.get("canonical_capability_id")
        if not isinstance(canonical_id, str) or not canonical_id:
            raise DecisionError(
                "schema 2 create decisions require canonical_capability_id"
            )
    elif schema_version == 2 and value.get("canonical_capability_id") is not None:
        raise DecisionError(
            "schema 2 canonical_capability_id is only valid for create decisions"
        )
    if not isinstance(value.get("rationale"), str) or len(value["rationale"].strip()) < 40:
        raise DecisionError("decision rationale must contain a concrete comparison")
    source_refs = value.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs or any(
        not isinstance(source, str) or not source for source in source_refs
    ):
        raise DecisionError("decision needs non-empty source_refs")
    value = dict(value)
    value["candidate_id"] = candidate_id
    value["fingerprint"] = normalize_fingerprint(value.get("fingerprint"))
    if schema_version == 2 and value["outcome"] == "not_promoted":
        conditions = value.get("reactivation_conditions")
        if not isinstance(conditions, list) or not conditions or any(
            not isinstance(condition, str) or not condition.strip()
            for condition in conditions
        ):
            raise DecisionError(
                "schema 2 not_promoted decisions require reactivation_conditions"
            )
    return value


def _validate_source_refs(root: Path, source_refs: list[str], *, require_official: bool) -> None:
    sources = {source["id"]: source for source in load_registry(root)}
    unknown = sorted(set(source_refs) - set(sources))
    if unknown:
        raise DecisionError(f"decision references an unregistered source: {', '.join(unknown)}")
    if require_official and not any(sources[source_id]["trust"] == "official" for source_id in source_refs):
        raise DecisionError("create and update decisions require at least one official source")


def apply_decision(root: Path, decision_path: Path) -> dict[str, Any]:
    decision = _validate_decision(load_json(decision_path))
    discovery_path = root / "candidates" / "inbox" / f"{decision['candidate_id']}.json"
    discovery = load_json(discovery_path)
    if not isinstance(discovery, dict) or discovery.get("id") != decision["candidate_id"]:
        raise DecisionError("decision candidate_id must name an inbox discovery")

    catalog = _catalog(root)
    taxonomy = (
        load_json(root / "catalog" / "taxonomy.json")
        if catalog["schema_version"] == 2
        else None
    )
    target_id = decision.get("target_capability_id")
    target = _internal_entry(catalog, target_id) if isinstance(target_id, str) else None
    outcome = decision["outcome"]
    is_not_promoted = outcome in {"discard", "not_promoted"}
    _validate_source_refs(
        root,
        decision["source_refs"],
        require_official=outcome in {"create", "update"},
    )
    if outcome in {"merge", "update"} and target is None:
        raise DecisionError(f"{outcome} requires an internal target_capability_id")
    if (is_not_promoted or outcome == "create") and target_id is not None:
        raise DecisionError(f"{outcome} must not set target_capability_id")

    artifact = _validated_artifact(decision.get("artifact")) if outcome in {"create", "update"} else None
    candidate = {
        "candidate_id": decision["candidate_id"],
        "fingerprint": decision["fingerprint"],
        "artifact": artifact,
    }
    if outcome == "update":
        candidate["proposed_target_capability_id"] = target_id
    recommendation = recommend_decision(candidate, catalog)
    if recommendation["outcome"] == "discard_exact" and outcome in {"create", "update"}:
        raise DecisionError("an exact bundle duplicate cannot be created or used as an update")

    artifact_previous: dict[str, Any] | None = None
    marketplace: dict[str, Any] | None = None
    if outcome == "create":
        if decision["schema_version"] == 2:
            capability_id = decision["canonical_capability_id"]
            if not re.fullmatch(taxonomy["canonical_id"]["pattern"], capability_id):
                raise DecisionError("canonical_capability_id is invalid")
        else:
            capability_id = f"{artifact['plugin_id']}:{artifact['skill_name']}"
        if _internal_entry(catalog, capability_id):
            raise DecisionError("create capability already exists; choose update or merge")
        entry = {
            "id": capability_id,
            "plugin_id": artifact["plugin_id"],
            "skill_name": artifact["skill_name"],
            "artifact_sha256": bundle_hash(artifact),
            "fingerprint": decision["fingerprint"],
            "source_refs": sorted(set(decision["source_refs"])),
            "revision": 1,
            "created_at": decision["reviewed_at"],
            "updated_at": decision["reviewed_at"],
            "managed_files": sorted(artifact["files"]),
        }
        if catalog["schema_version"] == 2:
            classification = decision.get("classification")
            _validate_classification_for_decision(
                classification,
                taxonomy,
                capability_id,
            )
            entry.update(
                {
                    "aliases": decision.get("aliases", []),
                    "classification": classification,
                    "merged_source_refs": [],
                    "variants": decision.get("variants", []),
                }
            )
        catalog["internal"].append(entry)
        marketplace = _marketplace_with_plugin(root, artifact["plugin_id"], artifact["plugin_manifest"])
    elif outcome == "update":
        capability_id = target["id"]
        if (
            artifact["plugin_id"] != target["plugin_id"]
            or artifact["skill_name"] != target["skill_name"]
        ):
            raise DecisionError(
                "update artifact packaging must match the target capability"
            )
        artifact_previous = dict(target)
        target.update(
            {
                "artifact_sha256": bundle_hash(artifact),
                "fingerprint": decision["fingerprint"],
                "source_refs": sorted(set(target.get("source_refs", []) + decision["source_refs"])),
                "revision": int(target.get("revision", 0)) + 1,
                "updated_at": decision["reviewed_at"],
                "managed_files": sorted(artifact["files"]),
            }
        )
        if catalog["schema_version"] == 2 and decision.get("classification") is not None:
            _validate_classification_for_decision(
                decision["classification"],
                taxonomy,
                capability_id,
            )
            target["classification"] = decision["classification"]
        marketplace = _marketplace_with_plugin(root, artifact["plugin_id"], artifact["plugin_manifest"])
    elif outcome == "merge":
        capability_id = target["id"]
        target["source_refs"] = sorted(set(target.get("source_refs", []) + decision["source_refs"]))
        target["updated_at"] = decision["reviewed_at"]
        if catalog["schema_version"] == 2:
            target["merged_source_refs"] = sorted(
                set(target.get("merged_source_refs", []) + decision["source_refs"])
            )
    else:
        capability_id = None

    if taxonomy is not None:
        _validate_catalog_for_decision(catalog, taxonomy)
    if artifact is not None:
        assert marketplace is not None
        _write_artifact(root, artifact, artifact_previous)
        atomic_write_json(
            root / ".agents" / "plugins" / "marketplace.json", marketplace
        )
    atomic_write_json(root / "catalog" / "capabilities.json", catalog)
    record = {
        "schema_version": decision["schema_version"],
        "candidate_id": decision["candidate_id"],
        "reviewed_by": "codex",
        "reviewed_at": decision["reviewed_at"],
        "outcome": outcome,
        "target_capability_id": capability_id,
        "rationale": decision["rationale"],
        "source_refs": decision["source_refs"],
        "fingerprint": decision["fingerprint"],
        "recommendation": recommendation,
    }
    if outcome == "not_promoted":
        record["reactivation_conditions"] = decision["reactivation_conditions"]
    record_name = f"{decision['reviewed_at'].replace(':', '-')}-{decision['candidate_id']}.json"
    record_path = root / "decisions" / "records" / record_name
    atomic_write_json(record_path, record)
    discovery["review_status"] = "applied"
    discovery["decision_outcome"] = outcome
    discovery["decision_record"] = record_path.relative_to(root).as_posix()
    atomic_write_json(discovery_path, discovery)
    return record
