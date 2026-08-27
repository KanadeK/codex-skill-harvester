from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.decisions import bundle_hash, recommend_decision


RELEASE_FINGERPRINT = {
    "goal": "audit published github release evidence",
    "triggers": ["is this github release actually complete"],
    "inputs": ["repository", "release tag"],
    "outputs": ["evidence matrix", "gap report"],
    "tools": ["gh"],
    "side_effects": ["read-only"],
    "platforms": ["github"],
}


def artifact(skill_text: str) -> dict[str, object]:
    return {
        "plugin_id": "github-release-evidence",
        "plugin_manifest": {
            "name": "github-release-evidence",
            "version": "0.1.0",
            "description": "Audit GitHub release publication evidence.",
            "author": {"name": "KanadeK"},
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
        "files": {"SKILL.md": skill_text},
    }


def catalog() -> dict[str, object]:
    old_artifact = artifact("---\nname: audit-github-release\ndescription: Old\n---\nOld workflow\n")
    return {
        "schema_version": 1,
        "internal": [
            {
                "id": "github-release-evidence:audit-github-release",
                "plugin_id": "github-release-evidence",
                "skill_name": "audit-github-release",
                "artifact_sha256": bundle_hash(old_artifact),
                "fingerprint": RELEASE_FINGERPRINT,
                "source_refs": ["github-cli-release-view"],
                "revision": 1,
            }
        ],
        "external": [
            {
                "id": "openai:gh-fix-ci",
                "artifact_sha256": "f" * 64,
                "fingerprint": {
                    "goal": "repair failing github actions checks",
                    "triggers": ["fix github ci"],
                    "inputs": ["pull request"],
                    "outputs": ["diagnosis", "approved code fix"],
                    "tools": ["gh"],
                    "side_effects": ["repository changes"],
                    "platforms": ["github"],
                },
            }
        ],
    }


class DecisionRecommendationTests(unittest.TestCase):
    def test_exact_bundle_duplicate_is_distinct_from_semantic_duplicate(self) -> None:
        existing_text = "---\nname: audit-github-release\ndescription: Old\n---\nOld workflow\n"
        candidate = {
            "candidate_id": "exact",
            "fingerprint": RELEASE_FINGERPRINT,
            "artifact": artifact(existing_text),
        }

        recommendation = recommend_decision(candidate, catalog())

        self.assertEqual(recommendation["outcome"], "discard_exact")
        self.assertEqual(
            recommendation["matches"], ["github-release-evidence:audit-github-release"]
        )

    def test_same_codex_normalized_fingerprint_recommends_semantic_merge(self) -> None:
        candidate = {
            "candidate_id": "semantic",
            "fingerprint": RELEASE_FINGERPRINT,
            "artifact": artifact(
                "---\nname: audit-github-release\ndescription: New wording\n---\nDifferent prose\n"
            ),
        }

        recommendation = recommend_decision(candidate, catalog())

        self.assertEqual(recommendation["outcome"], "merge_semantic")
        self.assertEqual(
            recommendation["matches"], ["github-release-evidence:audit-github-release"]
        )

    def test_explicit_existing_target_recommends_update(self) -> None:
        candidate = {
            "candidate_id": "update",
            "proposed_target_capability_id": "github-release-evidence:audit-github-release",
            "fingerprint": RELEASE_FINGERPRINT,
            "artifact": artifact(
                "---\nname: audit-github-release\ndescription: Updated\n---\nUpdated workflow\n"
            ),
        }

        recommendation = recommend_decision(candidate, catalog())

        self.assertEqual(recommendation["outcome"], "update_existing")
        self.assertEqual(
            recommendation["matches"], ["github-release-evidence:audit-github-release"]
        )

    def test_unmatched_capability_recommends_new(self) -> None:
        candidate = {
            "candidate_id": "new",
            "fingerprint": {
                "goal": "turn api changelogs into migration rehearsals",
                "triggers": ["rehearse this api upgrade"],
                "inputs": ["changelog", "current version", "target version"],
                "outputs": ["migration rehearsal"],
                "tools": ["local shell"],
                "side_effects": ["temporary files"],
                "platforms": ["cross-platform"],
            },
            "artifact": artifact(
                "---\nname: rehearse-api-upgrade\ndescription: Rehearse an API upgrade.\n---\nWorkflow\n"
            ),
        }

        recommendation = recommend_decision(candidate, catalog())

        self.assertEqual(recommendation["outcome"], "create_new")
        self.assertEqual(recommendation["matches"], [])


if __name__ == "__main__":
    unittest.main()
