from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrandReleaseTests(unittest.TestCase):
    def test_readmes_present_the_harvester_engine_and_human_frontstage(self) -> None:
        chinese = (ROOT / "README.md").read_text(encoding="utf-8")
        english = (ROOT / "README.en.md").read_text(encoding="utf-8")

        self.assertTrue(chinese.startswith("# Codex Skill Harvester"))
        self.assertIn("[English](README.en.md)", chinese)
        self.assertIn("后台发现、证据、去重与维护引擎", chinese)
        self.assertIn(
            "[Skills for Humans / 给人类的 Skill](https://github.com/KanadeK/skills-for-humans)",
            chinese,
        )
        self.assertIn(
            "[v0.2.0](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.2.0)",
            chinese,
        )
        self.assertIn("是已保留的历史技术原型", chinese)
        self.assertNotIn("AI 没长手，但可以教你把日子过明白。", chinese)
        self.assertIn("[工程状态](docs/engineering-status.md)", chinese)

        self.assertTrue(english.startswith("# Codex Skill Harvester"))
        self.assertIn("[简体中文](README.md)", english)
        self.assertIn("background discovery, evidence, deduplication, and maintenance engine", english)
        self.assertIn(
            "[Skills for Humans](https://github.com/KanadeK/skills-for-humans)",
            english,
        )
        self.assertIn(
            "[v0.2.0](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.2.0)",
            english,
        )
        self.assertIn("remains an immutable historical technical prototype", english)

    def test_skill_catalog_covers_every_stable_capability(self) -> None:
        catalog = json.loads(
            (ROOT / "catalog" / "capabilities.json").read_text(encoding="utf-8")
        )
        skill_catalog = (ROOT / "SKILLS.md").read_text(encoding="utf-8")

        self.assertEqual(len(catalog["internal"]), 17)
        for capability in catalog["internal"]:
            self.assertIn(capability["id"], skill_catalog)
        self.assertGreaterEqual(skill_catalog.count("示例提问"), 17)
        self.assertIn("发布状态", skill_catalog)
        self.assertIn("安全边界", skill_catalog)
        self.assertNotIn("v0.2.0 candidate", skill_catalog)
        self.assertGreaterEqual(skill_catalog.count("v0.2.0 published"), 16)

    def test_v020_is_the_single_current_release_version(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        manifests = sorted(ROOT.glob("plugins/*/.codex-plugin/plugin.json"))

        self.assertEqual(project["project"]["version"], "0.2.0")
        self.assertEqual(len(manifests), 11)
        for manifest in manifests:
            value = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(value["version"], "0.2.0", manifest.as_posix())

        marketplace = json.loads(
            (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marketplace["interface"]["displayName"], "会过日子 · Human Skills")

    def test_public_repository_metadata_matches_the_engine_identity(self) -> None:
        metadata = json.loads(
            (ROOT / ".github" / "repository-metadata.json").read_text(
                encoding="utf-8"
            )
        )
        expected_topics = {
            "agent-skills",
            "automation",
            "codex",
            "openai",
            "python",
            "github-actions",
            "data-pipeline",
            "deduplication",
            "skill-maintenance",
        }

        self.assertEqual(
            metadata["description"],
            "Incremental evidence, deduplication, and review engine for maintaining Codex and Open Agent Skills.",
        )
        self.assertTrue(expected_topics <= set(metadata["topics"]))
        self.assertNotIn("daily-life", metadata["topics"])

    def test_v020_changelog_and_engineering_handoff_exist(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        engineering = (ROOT / "docs" / "engineering-status.md").read_text(
            encoding="utf-8"
        )
        adoption = (ROOT / "docs" / "plan-adoption-audit.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("## 0.2.0", changelog)
        for heading in ("### Added", "### Changed", "### Fixed", "### Security"):
            self.assertIn(heading, changelog)
        self.assertIn("9 个 Daily Life Skills", changelog)
        self.assertIn("SQLite v4", changelog)
        self.assertIn("17 Skills", engineering)
        self.assertIn("11 Plugins", engineering)
        self.assertIn("63", engineering)
        self.assertIn("Released version: v0.2.0", engineering)
        self.assertNotIn("Candidate version: v0.2.0", engineering)
        self.assertIn(
            "[state/harvest.sqlite3](../state/harvest.sqlite3)", engineering
        )
        self.assertNotIn(
            "SQLite schema 3 is the sole runtime authority", adoption
        )

    def test_final_release_attestation_records_remote_publication(self) -> None:
        paths = sorted((ROOT / "runs").glob("*-v0.2.0-attestation.json"))
        self.assertEqual(len(paths), 1)
        attestation = json.loads(paths[0].read_text(encoding="utf-8"))

        self.assertEqual(attestation["report_type"], "release-attestation")
        self.assertEqual(
            attestation["release"]["tag_commit_sha"],
            "ef4bd07bb1d5465ed1f26e7dfe478681c0193042",
        )
        self.assertTrue(attestation["release"]["immutable"])
        self.assertEqual(len(attestation["release"]["assets"]), 13)
        self.assertEqual(attestation["verification"]["tests"], 152)
        self.assertEqual(attestation["verification"]["live_skill_result"], "complete")


if __name__ == "__main__":
    unittest.main()
