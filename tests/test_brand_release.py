from __future__ import annotations

import json
import sys
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrandReleaseTests(unittest.TestCase):
    def test_chinese_and_english_storefronts_present_the_approved_brand(self) -> None:
        chinese = (ROOT / "README.md").read_text(encoding="utf-8")
        english = (ROOT / "README.en.md").read_text(encoding="utf-8")

        self.assertTrue(chinese.startswith("# 会过日子 · Human Skills"))
        self.assertIn("AI 没长手，但可以教你把日子过明白。", chinese)
        self.assertIn("[English](README.en.md)", chinese)
        self.assertIn("买三天菜", chinese)
        self.assertIn("这桶衣服怎么洗", chinese)
        self.assertIn("用现有食材安排晚饭", chinese)
        self.assertIn("不会替你完成物理动作", chinese)
        self.assertIn("[Skill 目录](SKILLS.md)", chinese)
        self.assertIn("[工程状态](docs/engineering-status.md)", chinese)

        self.assertTrue(english.startswith("# Human Skills · 会过日子"))
        self.assertIn("[简体中文](README.md)", english)
        self.assertIn("AI has no hands", english)
        self.assertIn("[Skill Catalog](SKILLS.md)", english)

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

    def test_public_repository_metadata_matches_the_launch_identity(self) -> None:
        metadata = json.loads(
            (ROOT / ".github" / "repository-metadata.json").read_text(
                encoding="utf-8"
            )
        )
        expected_topics = {
            "agent-skills",
            "codex",
            "openai",
            "life-skills",
            "daily-life",
            "bilingual",
            "chinese",
            "cooking",
            "laundry",
            "grocery-shopping",
        }

        self.assertEqual(
            metadata["description"],
            "会过日子 · Human Skills — Evidence-reviewed bilingual Codex Skills for everyday life and software.",
        )
        self.assertTrue(expected_topics <= set(metadata["topics"]))
        self.assertNotIn("skill-harvester-only", metadata["topics"])

    def test_v020_changelog_and_engineering_handoff_exist(self) -> None:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        engineering = (ROOT / "docs" / "engineering-status.md").read_text(
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


if __name__ == "__main__":
    unittest.main()
