from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


REQUIRED_FACETS = (
    "domain",
    "intent",
    "inputs",
    "outputs",
    "tools",
    "platforms",
    "side_effects",
    "risk",
    "volatility",
    "maturity",
    "trust",
)


class TaxonomyError(ValueError):
    pass


def _string_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise TaxonomyError(f"{label} must contain unique non-empty strings")
    return value


def validate_taxonomy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise TaxonomyError("taxonomy must use schema_version 1")
    version = value.get("taxonomy_version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise TaxonomyError("taxonomy_version must use semantic versioning")

    canonical = value.get("canonical_id")
    family = value.get("primary_family")
    if (
        not isinstance(canonical, dict)
        or canonical.get("immutable") is not True
        or not isinstance(canonical.get("pattern"), str)
    ):
        raise TaxonomyError("taxonomy canonical id contract is invalid")
    if not isinstance(family, dict) or not isinstance(family.get("pattern"), str):
        raise TaxonomyError("taxonomy primary family contract is invalid")
    try:
        re.compile(canonical["pattern"])
        re.compile(family["pattern"])
    except re.error as error:
        raise TaxonomyError("taxonomy contains an invalid regular expression") from error

    facets = value.get("facets")
    if not isinstance(facets, dict) or set(facets) != set(REQUIRED_FACETS):
        raise TaxonomyError("taxonomy facets do not match the required dimensions")
    for name in REQUIRED_FACETS:
        rule = facets[name]
        if not isinstance(rule, dict):
            raise TaxonomyError(f"taxonomy facet {name} must be an object")
        if rule.get("cardinality") not in {"exactly-one", "one-or-more"}:
            raise TaxonomyError(f"taxonomy facet {name} has invalid cardinality")
        if not isinstance(rule.get("extensible"), bool):
            raise TaxonomyError(f"taxonomy facet {name} must declare extensible")
        values = _string_list(rule.get("values"), f"taxonomy facet {name} values")
        if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item) for item in values):
            raise TaxonomyError(f"taxonomy facet {name} values must use kebab-case")
    return value


def validate_classification(
    value: Any, taxonomy: dict[str, Any], capability_id: str
) -> None:
    if not isinstance(value, dict):
        raise TaxonomyError(f"capability {capability_id} classification must be an object")
    family = value.get("primary_family")
    if not isinstance(family, str) or not re.fullmatch(
        taxonomy["primary_family"]["pattern"], family
    ):
        raise TaxonomyError(f"capability {capability_id} primary family is invalid")
    facets = value.get("facets")
    if not isinstance(facets, dict) or set(facets) != set(REQUIRED_FACETS):
        raise TaxonomyError(f"capability {capability_id} facets are incomplete")
    for name in REQUIRED_FACETS:
        selected = _string_list(facets[name], f"capability {capability_id} facet {name}")
        rule = taxonomy["facets"][name]
        if rule["cardinality"] == "exactly-one" and len(selected) != 1:
            raise TaxonomyError(
                f"capability {capability_id} facet {name} requires exactly one value"
            )
        unknown = sorted(set(selected) - set(rule["values"]))
        if unknown:
            raise TaxonomyError(
                f"capability {capability_id} has unregistered facet value: "
                + ", ".join(unknown)
            )


def validate_catalog_taxonomy(
    catalog: Any, taxonomy_value: Any
) -> dict[str, Any]:
    taxonomy = validate_taxonomy(taxonomy_value)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 2:
        raise TaxonomyError("catalog must use schema_version 2")
    if catalog.get("taxonomy_version") != taxonomy["taxonomy_version"]:
        raise TaxonomyError("catalog taxonomy_version does not match the registry")
    internal = catalog.get("internal")
    external = catalog.get("external")
    if not isinstance(internal, list) or not isinstance(external, list):
        raise TaxonomyError("catalog must contain internal and external lists")

    seen: set[str] = set()
    for entry in internal + external:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise TaxonomyError("catalog capability id is missing")
        capability_id = entry["id"]
        if capability_id in seen:
            raise TaxonomyError(f"duplicate canonical capability id: {capability_id}")
        seen.add(capability_id)
        if not re.fullmatch(taxonomy["canonical_id"]["pattern"], capability_id):
            raise TaxonomyError(f"canonical capability id is invalid: {capability_id}")
        validate_classification(entry.get("classification"), taxonomy, capability_id)
        for field in ("aliases", "variants", "merged_source_refs"):
            field_value = entry.get(field)
            if not isinstance(field_value, list) or any(
                not isinstance(item, str) or not item for item in field_value
            ):
                raise TaxonomyError(
                    f"capability {capability_id} {field} must be a string list"
                )
    return {
        "schema_version": 2,
        "taxonomy_version": taxonomy["taxonomy_version"],
        "capabilities": len(seen),
    }


def migrate_catalog_v1_to_v2(
    catalog: Any, migration: Any, taxonomy_value: Any
) -> dict[str, Any]:
    taxonomy = validate_taxonomy(taxonomy_value)
    if isinstance(catalog, dict) and catalog.get("schema_version") == 2:
        validate_catalog_taxonomy(catalog, taxonomy)
        return deepcopy(catalog)
    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1:
        raise TaxonomyError("catalog migration supports schema_version 1 or 2")
    if (
        not isinstance(migration, dict)
        or migration.get("schema_version") != 1
        or migration.get("target_catalog_schema") != 2
        or migration.get("taxonomy_version") != taxonomy["taxonomy_version"]
        or not isinstance(migration.get("capabilities"), dict)
    ):
        raise TaxonomyError("catalog migration map is invalid")

    migrated = deepcopy(catalog)
    migrated["schema_version"] = 2
    migrated["taxonomy_version"] = taxonomy["taxonomy_version"]
    for entry in migrated.get("internal", []) + migrated.get("external", []):
        capability_id = entry.get("id")
        mapping = migration["capabilities"].get(capability_id)
        if not isinstance(mapping, dict) or not isinstance(
            mapping.get("classification"), dict
        ):
            raise TaxonomyError(
                f"catalog migration needs a classification mapping for {capability_id}"
            )
        for field in ("classification", "aliases", "variants", "merged_source_refs"):
            if field not in mapping:
                raise TaxonomyError(
                    f"catalog migration mapping for {capability_id} is missing {field}"
                )
            entry[field] = deepcopy(mapping[field])
    validate_catalog_taxonomy(migrated, taxonomy)
    return migrated
