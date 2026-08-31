from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

from .io import load_json
from .sources import load_registry


class ScenarioBankError(ValueError):
    pass


EXPECTED_FAMILIES = {
    "fresh-market-and-grocery-shopping",
    "laundry-and-clothing-care",
    "home-cooking-and-meal-preparation",
}
TERMINAL_OUTCOMES = {"create", "update", "merge", "not_promoted"}
REQUIRED_LISTS = (
    "critical_inputs",
    "locality_conditions",
    "equipment_conditions",
    "observable_completion",
    "recovery",
    "safety_stop",
    "source_refs",
)


def _string_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ScenarioBankError(f"{label} must be a non-empty string list")
    return value


def load_scenario_bank(
    root: Path, *, enforce_coverage: bool = True
) -> dict[str, Any]:
    value = load_json(root / "catalog" / "scenario-bank.json")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ScenarioBankError("scenario bank must use schema_version 1")
    families = value.get("families")
    scenarios = value.get("scenarios")
    if not isinstance(families, list) or not isinstance(scenarios, list):
        raise ScenarioBankError("scenario bank families and scenarios must be lists")
    family_ids: set[str] = set()
    for family in families:
        if (
            not isinstance(family, dict)
            or not isinstance(family.get("id"), str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", family["id"])
            or not isinstance(family.get("plugin_id"), str)
            or family["plugin_id"] != family["id"]
            or family["id"] in family_ids
        ):
            raise ScenarioBankError("scenario family is invalid")
        family_ids.add(family["id"])

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in scenarios:
        if not isinstance(raw, dict):
            raise ScenarioBankError("scenario records must be objects")
        scenario = dict(raw)
        scenario_id = scenario.get("id")
        if (
            not isinstance(scenario_id, str)
            or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", scenario_id)
            or scenario_id in seen_ids
        ):
            raise ScenarioBankError("scenario ids must be unique kebab-case")
        seen_ids.add(scenario_id)
        if scenario.get("family") not in family_ids:
            raise ScenarioBankError(f"scenario {scenario_id} family is invalid")
        if scenario.get("mode") not in {"plan", "live", "recovery"}:
            raise ScenarioBankError(f"scenario {scenario_id} mode is invalid")
        request = scenario.get("user_request")
        if (
            not isinstance(request, dict)
            or not isinstance(request.get("zh"), str)
            or not request["zh"].strip()
            or (
                "en" in request
                and (not isinstance(request["en"], str) or not request["en"].strip())
            )
        ):
            raise ScenarioBankError(f"scenario {scenario_id} user request is invalid")
        for field in REQUIRED_LISTS:
            scenario[field] = _string_list(
                scenario.get(field), f"scenario {scenario_id} {field}"
            )
        if scenario.get("outcome") not in TERMINAL_OUTCOMES:
            raise ScenarioBankError(
                f"scenario {scenario_id} needs a terminal outcome"
            )
        rationale = scenario.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 40:
            raise ScenarioBankError(f"scenario {scenario_id} rationale is incomplete")
        if scenario["outcome"] == "not_promoted":
            if scenario.get("capability_id") is not None:
                raise ScenarioBankError(
                    f"scenario {scenario_id} not_promoted cannot target a capability"
                )
            scenario["reactivation_conditions"] = _string_list(
                scenario.get("reactivation_conditions"),
                f"scenario {scenario_id} reactivation_conditions",
            )
        elif not isinstance(scenario.get("capability_id"), str):
            raise ScenarioBankError(
                f"scenario {scenario_id} needs a capability target"
            )
        normalized.append(scenario)

    catalog = load_json(root / "catalog" / "capabilities.json")
    if not isinstance(catalog, dict) or not isinstance(catalog.get("internal"), list):
        raise ScenarioBankError("capability catalog is invalid")
    capability_ids = {entry["id"] for entry in catalog["internal"]}
    source_ids = {source["id"] for source in load_registry(root)}
    created: set[str] = set()
    for scenario in normalized:
        unknown_sources = sorted(set(scenario["source_refs"]) - source_ids)
        if unknown_sources:
            raise ScenarioBankError(
                f"scenario {scenario['id']} references unknown sources: "
                + ", ".join(unknown_sources)
            )
        capability_id = scenario.get("capability_id")
        if capability_id is not None and capability_id not in capability_ids:
            raise ScenarioBankError(
                f"scenario {scenario['id']} references an unknown capability"
            )
        if scenario["outcome"] == "create":
            if capability_id in created:
                raise ScenarioBankError(
                    f"capability {capability_id} has multiple create scenarios"
                )
            created.add(capability_id)

    by_family = Counter(scenario["family"] for scenario in normalized)
    outcomes = Counter(scenario["outcome"] for scenario in normalized)
    if enforce_coverage:
        if family_ids != EXPECTED_FAMILIES:
            raise ScenarioBankError("scenario bank must contain the three Daily Life families")
        if len(normalized) < 60 or any(by_family[family] < 20 for family in family_ids):
            raise ScenarioBankError(
                "scenario bank requires at least 60 scenarios and 20 per family"
            )
    return {
        "schema_version": 1,
        "scenarios": len(normalized),
        "by_family": dict(sorted(by_family.items())),
        "outcomes": dict(sorted(outcomes.items())),
        "pending": 0,
        "created_capabilities": sorted(created),
    }
