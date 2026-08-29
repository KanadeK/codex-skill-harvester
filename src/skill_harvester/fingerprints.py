from __future__ import annotations

import re
import unicodedata
from typing import Any


FINGERPRINT_FIELDS = (
    "goal",
    "triggers",
    "inputs",
    "outputs",
    "tools",
    "side_effects",
    "platforms",
)

FINGERPRINT_WEIGHTS = {
    "goal": 0.30,
    "triggers": 0.15,
    "inputs": 0.10,
    "outputs": 0.15,
    "tools": 0.08,
    "side_effects": 0.12,
    "platforms": 0.10,
}


class FingerprintError(ValueError):
    pass


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def normalize_fingerprint(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FingerprintError("fingerprint must be an object")
    normalized: dict[str, Any] = {}
    for field in FINGERPRINT_FIELDS:
        field_value = value.get(field)
        if field == "goal":
            if not isinstance(field_value, str) or not field_value.strip():
                raise FingerprintError("fingerprint goal must be a non-empty string")
            normalized[field] = _normalized_text(field_value)
            continue
        if not isinstance(field_value, list) or not field_value:
            raise FingerprintError(f"fingerprint {field} must be a non-empty list")
        if any(not isinstance(item, str) or not item.strip() for item in field_value):
            raise FingerprintError(
                f"fingerprint {field} values must be non-empty strings"
            )
        normalized[field] = sorted({_normalized_text(item) for item in field_value})
    return normalized


def _catalog_entries(catalog: Any) -> list[dict[str, Any]]:
    if not isinstance(catalog, dict) or catalog.get("schema_version") not in {1, 2}:
        raise FingerprintError("catalog must use schema_version 1 or 2")
    internal = catalog.get("internal")
    external = catalog.get("external")
    if not isinstance(internal, list) or not isinstance(external, list):
        raise FingerprintError("catalog must contain internal and external lists")
    entries = internal + external
    if any(
        not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
        for entry in entries
    ):
        raise FingerprintError("catalog entries must have string ids")
    return entries


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value))


def _field_similarity(field: str, left: Any, right: Any) -> float:
    if field == "goal":
        left_terms = _terms(left)
        right_terms = _terms(right)
    else:
        left_terms = {term for item in left for term in _terms(item)}
        right_terms = {term for item in right for term in _terms(item)}
    union = left_terms | right_terms
    return len(left_terms & right_terms) / len(union) if union else 0.0


def recall_capabilities(
    fingerprint: Any, catalog: Any, *, limit: int = 30
) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise FingerprintError("recall limit must be between 1 and 50")
    normalized = normalize_fingerprint(fingerprint)
    scored: list[dict[str, Any]] = []
    for entry in _catalog_entries(catalog):
        existing = normalize_fingerprint(entry.get("fingerprint"))
        score = sum(
            FINGERPRINT_WEIGHTS[field]
            * _field_similarity(field, normalized[field], existing[field])
            for field in FINGERPRINT_FIELDS
        )
        if score:
            scored.append({"id": entry["id"], "score": round(score, 6)})
    return sorted(scored, key=lambda item: (-item["score"], item["id"]))[:limit]
