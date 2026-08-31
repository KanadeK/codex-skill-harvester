from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.decisions import DecisionError, apply_decision
from skill_harvester.runtime_store import create_empty_runtime, open_runtime_store

from _support import read_json, write_runtime_discovery


FINGERPRINT = {
    "goal": "audit published github release evidence",
    "triggers": ["is this github release actually complete"],
    "inputs": ["repository", "release tag"],
    "outputs": ["evidence matrix", "gap report"],
    "tools": ["gh"],
    "side_effects": ["read-only"],
    "platforms": ["github"],
}

CLASSIFICATION = {
    "primary_family": "software.release-assurance",
    "facets": {
        "domain": ["software"],
        "intent": ["validate"],
        "inputs": ["repository", "release"],
        "outputs": ["report", "evidence"],
        "tools": ["gh", "python"],
        "platforms": ["github", "codex", "windows"],
        "side_effects": ["network-read", "local-write"],
        "risk": ["standard"],
        "volatility": ["fast-moving"],
        "maturity": ["published"],
        "trust": ["official", "primary"],
    },
}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def create_decision(root: Path, *, reviewed_by: str = "codex") -> Path:
    candidate_id = "real-source-candidate"
    write_json(
        root / "sources" / "registry.json",
        {
            "schema_version": 1,
            "sources": [
                {
                    "id": "github-cli-release-view",
                    "adapter": "document",
                    "url": "https://cli.github.com/manual/gh_release_view",
                    "trust": "official",
                    "tier": "T1",
                    "authority": "vendor-docs",
                    "license": {"status": "known", "identifier": "MIT"},
                },
                {
                    "id": "github-rest-releases",
                    "adapter": "document",
                    "url": "https://docs.github.com/en/rest/releases/releases",
                    "trust": "official",
                    "tier": "T1",
                    "authority": "vendor-docs",
                    "license": {"status": "facts-only", "identifier": "CC-BY-4.0"},
                },
            ],
        },
    )
    create_empty_runtime(root)
    write_runtime_discovery(
        root,
        {
                "schema_version": 1,
                "id": candidate_id,
                "source_id": "github-cli-release-view",
                "source_revision": "fixture-v1",
                "observed_at": "2026-08-27T07:00:00Z",
                "title": "Fixture source candidate",
                "canonical_url": "https://cli.github.com/manual/gh_release_view",
                "evidence_sha256": "a" * 64,
                "trust": "official",
                "authority": "vendor-docs",
                "license": {"status": "known", "identifier": "MIT"},
                "extracted_facts": [],
                "review_status": "pending",
                "fingerprint": FINGERPRINT,
            },
        queue="official-gap",
    )
    decision = {
        "schema_version": 1,
        "candidate_id": candidate_id,
        "reviewed_by": reviewed_by,
        "reviewed_at": "2026-08-27T07:00:00Z",
        "outcome": "create",
        "target_capability_id": None,
        "rationale": (
            "Compared internal catalog and openai:gh-fix-ci; release publication evidence is a "
            "distinct read-only task and the official GitHub sources support each check."
        ),
        "source_refs": ["github-cli-release-view", "github-rest-releases"],
        "fingerprint": FINGERPRINT,
        "artifact": {
            "origin": "original-synthesis",
            "plugin_id": "github-release-evidence",
            "plugin_manifest": {
                "name": "github-release-evidence",
                "version": "0.1.0",
                "description": "Audit GitHub release publication evidence.",
                "author": {"name": "KanadeK"},
                "license": "MIT",
                "skills": "./skills/",
                "interface": {
                    "displayName": "GitHub Release Evidence",
                    "shortDescription": "Audit release evidence and report gaps",
                    "longDescription": "Read-only GitHub release evidence audits.",
                    "developerName": "KanadeK",
                    "category": "Developer Tools",
                    "capabilities": ["Read"],
                    "defaultPrompt": "Audit whether this GitHub release is complete.",
                },
            },
            "skill_name": "audit-github-release",
            "files": {
                "SKILL.md": (
                    "---\nname: audit-github-release\n"
                    "description: Audit whether an existing GitHub release is complete.\n---\n"
                    "Collect remote evidence and report gaps.\n"
                ),
                "references/sources.md": "# Sources\n\n- https://cli.github.com/manual/gh_release_view\n",
            },
        },
    }
    path = root / "candidates" / "reviewed" / f"{candidate_id}.json"
    write_json(path, decision)
    return path


class ApplyDecisionTests(unittest.TestCase):
    def test_create_writes_plugin_skill_catalog_marketplace_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root)

            result = apply_decision(root, decision_path)

            skill_root = (
                root
                / "plugins"
                / "github-release-evidence"
                / "skills"
                / "audit-github-release"
            )
            self.assertTrue((skill_root / "SKILL.md").is_file())
            self.assertTrue((skill_root / "references" / "sources.md").is_file())
            manifest = read_json(
                root
                / "plugins"
                / "github-release-evidence"
                / ".codex-plugin"
                / "plugin.json"
            )
            self.assertEqual(manifest["name"], "github-release-evidence")
            marketplace = read_json(root / ".agents" / "plugins" / "marketplace.json")
            self.assertEqual(marketplace["plugins"][0]["name"], "github-release-evidence")
            catalog = read_json(root / "catalog" / "capabilities.json")
            self.assertEqual(
                catalog["internal"][0]["id"],
                "github-release-evidence:audit-github-release",
            )
            with open_runtime_store(root) as store:
                self.assertEqual(store.decision_count(), 1)
                discovery = store.candidate("real-source-candidate")
                self.assertEqual(list(store.decisions())[0]["outcome"], "create")
            self.assertEqual(discovery["review_status"], "applied")
            self.assertEqual(result["outcome"], "create")

    def test_non_codex_review_cannot_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root, reviewed_by="heuristic")

            with self.assertRaisesRegex(DecisionError, "reviewed_by"):
                apply_decision(root, decision_path)

            self.assertFalse((root / "plugins").exists())

    def test_unregistered_source_reference_cannot_publish(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root)
            decision = read_json(decision_path)
            decision["source_refs"] = ["unregistered-source"]
            write_json(decision_path, decision)

            with self.assertRaisesRegex(DecisionError, "registered source"):
                apply_decision(root, decision_path)

            self.assertFalse((root / "plugins").exists())

    def test_schema_two_non_promotion_requires_reactivation_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root)
            decision = read_json(decision_path)
            decision["schema_version"] = 2
            decision["outcome"] = "not_promoted"
            decision.pop("artifact")
            write_json(decision_path, decision)

            with self.assertRaisesRegex(DecisionError, "reactivation"):
                apply_decision(root, decision_path)

            with open_runtime_store(root) as store:
                self.assertEqual(store.decision_count(), 0)

    def test_schema_two_non_promotion_is_retained_without_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "catalog" / "capabilities.json",
                {"schema_version": 1, "internal": [], "external": []},
            )
            decision_path = create_decision(root)
            decision = read_json(decision_path)
            decision["schema_version"] = 2
            decision["outcome"] = "not_promoted"
            decision["reactivation_conditions"] = [
                "Reconsider when an official source defines a distinct repeatable workflow."
            ]
            decision.pop("artifact")
            write_json(decision_path, decision)

            result = apply_decision(root, decision_path)

            self.assertEqual(result["outcome"], "not_promoted")
            self.assertEqual(
                result["reactivation_conditions"],
                decision["reactivation_conditions"],
            )
            self.assertFalse((root / "plugins").exists())
            with open_runtime_store(root) as store:
                discovery = store.candidate("real-source-candidate")
            self.assertEqual(discovery["decision_outcome"], "not_promoted")

    def test_schema_two_canonical_id_is_independent_of_packaging(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = Path(__file__).resolve().parents[1]
            taxonomy = read_json(repository / "catalog" / "taxonomy.json")
            write_json(root / "catalog" / "taxonomy.json", taxonomy)
            write_json(
                root / "catalog" / "capabilities.json",
                {
                    "schema_version": 2,
                    "taxonomy_version": taxonomy["taxonomy_version"],
                    "internal": [],
                    "external": [],
                },
            )
            create_path = create_decision(root)
            create = read_json(create_path)
            create["schema_version"] = 2
            create["canonical_capability_id"] = "software.release-audit"
            create["classification"] = CLASSIFICATION
            write_json(create_path, create)

            created = apply_decision(root, create_path)

            self.assertEqual(created["target_capability_id"], "software.release-audit")
            catalog = read_json(root / "catalog" / "capabilities.json")
            self.assertEqual(catalog["internal"][0]["id"], "software.release-audit")
            self.assertEqual(
                catalog["internal"][0]["plugin_id"], "github-release-evidence"
            )

            candidate_id = "changed-source-candidate"
            write_runtime_discovery(
                root,
                {
                        "schema_version": 1,
                        "id": candidate_id,
                        "source_id": "github-cli-release-view",
                        "source_revision": "fixture-v2",
                        "observed_at": "2026-08-27T08:00:00Z",
                        "title": "Changed fixture candidate",
                        "canonical_url": "https://cli.github.com/manual/gh_release_view?changed=1",
                        "evidence_sha256": "b" * 64,
                        "trust": "official",
                        "authority": "vendor-docs",
                        "license": {"status": "known", "identifier": "MIT"},
                        "extracted_facts": [],
                        "review_status": "pending",
                        "fingerprint": FINGERPRINT,
                    },
                queue="official-gap",
            )
            update = read_json(create_path)
            update["candidate_id"] = candidate_id
            update["reviewed_at"] = "2026-08-27T08:00:00Z"
            update["outcome"] = "update"
            update["target_capability_id"] = "software.release-audit"
            update.pop("canonical_capability_id")
            update["artifact"]["files"]["SKILL.md"] += "Revision 2.\n"
            update_path = root / "candidates" / "reviewed" / f"{candidate_id}.json"
            write_json(update_path, update)

            updated = apply_decision(root, update_path)

            self.assertEqual(updated["target_capability_id"], "software.release-audit")
            catalog = read_json(root / "catalog" / "capabilities.json")
            self.assertEqual(catalog["internal"][0]["revision"], 2)

    def test_schema_two_create_requires_a_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = Path(__file__).resolve().parents[1]
            taxonomy = read_json(repository / "catalog" / "taxonomy.json")
            write_json(root / "catalog" / "taxonomy.json", taxonomy)
            write_json(
                root / "catalog" / "capabilities.json",
                {
                    "schema_version": 2,
                    "taxonomy_version": taxonomy["taxonomy_version"],
                    "internal": [],
                    "external": [],
                },
            )
            decision_path = create_decision(root)
            decision = read_json(decision_path)
            decision["schema_version"] = 2
            decision["classification"] = CLASSIFICATION
            write_json(decision_path, decision)

            with self.assertRaisesRegex(DecisionError, "canonical_capability_id"):
                apply_decision(root, decision_path)

    def test_schema_two_catalog_validation_precedes_artifact_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = Path(__file__).resolve().parents[1]
            taxonomy = read_json(repository / "catalog" / "taxonomy.json")
            write_json(root / "catalog" / "taxonomy.json", taxonomy)
            write_json(
                root / "catalog" / "capabilities.json",
                {
                    "schema_version": 2,
                    "taxonomy_version": taxonomy["taxonomy_version"],
                    "internal": [],
                    "external": [],
                },
            )
            decision_path = create_decision(root)
            decision = read_json(decision_path)
            decision["schema_version"] = 2
            decision["canonical_capability_id"] = "software.release-audit"
            decision["classification"] = CLASSIFICATION
            decision["aliases"] = [""]
            write_json(decision_path, decision)

            with self.assertRaisesRegex(DecisionError, "aliases"):
                apply_decision(root, decision_path)

            self.assertFalse((root / "plugins").exists())
            self.assertFalse((root / ".agents" / "plugins").exists())


if __name__ == "__main__":
    unittest.main()
