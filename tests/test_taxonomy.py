from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.taxonomy import (
    TaxonomyError,
    migrate_catalog_v1_to_v2,
    validate_catalog_taxonomy,
)


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def legacy_catalog() -> dict[str, object]:
    return {
        "schema_version": 1,
        "internal": [
            {
                "id": "demo:audit-release",
                "artifact_sha256": "a" * 64,
                "fingerprint": {
                    "goal": "audit published github release evidence",
                    "triggers": ["audit this release"],
                    "inputs": ["repository"],
                    "outputs": ["report"],
                    "tools": ["gh"],
                    "side_effects": ["read-only"],
                    "platforms": ["github"],
                },
                "source_refs": ["official-doc"],
            }
        ],
        "external": [],
    }


def migration_map() -> dict[str, object]:
    return {
        "schema_version": 1,
        "target_catalog_schema": 2,
        "taxonomy_version": "1.0.0",
        "capabilities": {
            "demo:audit-release": {
                "aliases": ["release evidence audit"],
                "variants": [],
                "merged_source_refs": [],
                "classification": {
                    "primary_family": "software.release-assurance",
                    "facets": {
                        "domain": ["software"],
                        "intent": ["validate"],
                        "inputs": ["repository"],
                        "outputs": ["report"],
                        "tools": ["gh"],
                        "platforms": ["github"],
                        "side_effects": ["read-only"],
                        "risk": ["standard"],
                        "volatility": ["fast-moving"],
                        "maturity": ["published"],
                        "trust": ["official"],
                    },
                },
            }
        },
    }


class TaxonomyTests(unittest.TestCase):
    def test_catalog_v1_migration_is_complete_and_idempotent(self) -> None:
        taxonomy = read_json(ROOT / "catalog" / "taxonomy.json")
        migrated = migrate_catalog_v1_to_v2(
            legacy_catalog(), migration_map(), taxonomy
        )

        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["taxonomy_version"], "1.0.0")
        self.assertEqual(
            migrated["internal"][0]["classification"]["primary_family"],
            "software.release-assurance",
        )
        self.assertEqual(
            migrate_catalog_v1_to_v2(migrated, migration_map(), taxonomy),
            migrated,
        )

    def test_catalog_migration_fails_when_classification_is_missing(self) -> None:
        taxonomy = read_json(ROOT / "catalog" / "taxonomy.json")
        migration = migration_map()
        migration["capabilities"] = {}

        with self.assertRaisesRegex(TaxonomyError, "classification mapping"):
            migrate_catalog_v1_to_v2(legacy_catalog(), migration, taxonomy)

    def test_unknown_facet_value_fails_instead_of_becoming_a_category(self) -> None:
        taxonomy = read_json(ROOT / "catalog" / "taxonomy.json")
        catalog = migrate_catalog_v1_to_v2(
            legacy_catalog(), migration_map(), taxonomy
        )
        invalid = deepcopy(catalog)
        invalid["internal"][0]["classification"]["facets"]["domain"] = [
            "unregistered-domain"
        ]

        with self.assertRaisesRegex(TaxonomyError, "unregistered facet value"):
            validate_catalog_taxonomy(invalid, taxonomy)

    def test_current_repository_catalog_uses_the_current_taxonomy(self) -> None:
        taxonomy = read_json(ROOT / "catalog" / "taxonomy.json")
        catalog = read_json(ROOT / "catalog" / "capabilities.json")

        report = validate_catalog_taxonomy(catalog, taxonomy)

        self.assertEqual(report["taxonomy_version"], "1.0.0")
        self.assertEqual(report["capabilities"], 3)


if __name__ == "__main__":
    unittest.main()
