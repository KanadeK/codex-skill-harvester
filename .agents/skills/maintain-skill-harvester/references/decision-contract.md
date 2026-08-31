# Reviewed decision contract

Read this only when an observation has been explicitly normalized into a queued candidate and survived usefulness and provenance review.

## Required fields

```json
{
  "schema_version": 2,
  "candidate_id": "stable-normalized-candidate-id",
  "reviewed_by": "codex",
  "reviewed_at": "RFC-3339 timestamp",
  "outcome": "not_promoted|merge|update|create",
  "target_capability_id": "required for merge or update; null otherwise",
  "rationale": "Concrete semantic comparison and decision reason",
  "source_refs": ["registered-source-id"],
  "fingerprint": {
    "goal": "single normalized goal",
    "triggers": ["user-like trigger"],
    "inputs": ["required input"],
    "outputs": ["observable output"],
    "tools": ["tool or none"],
    "side_effects": ["read-only or concrete mutation"],
    "platforms": ["supported platform"]
  },
  "artifact": null
}
```

For `not_promoted`, add a non-empty `reactivation_conditions` string list describing evidence or demand that would justify reassessment.

For `create`, add a unique `canonical_capability_id`, a complete `classification` registered by `catalog/taxonomy.json`, and optional string-list `aliases` and `variants`. The canonical ID is stable and is not derived from the Plugin ID or Skill name.

For `create` and `update`, replace `artifact: null` with an object containing `"origin": "original-synthesis"`, the target Plugin ID and complete manifest, Skill name, original `SKILL.md` text, optional original reference files, and optional original scripts. Every artifact file path must be relative, remain inside the selected Skill directory, and have no executable source copied from public material. The current backend permits content updates at the target capability's existing Plugin/Skill location; packaging relocation requires a separately reviewed migration.

## Outcome rules

- `not_promoted`: unsuitable, unverifiable, exact duplicate, or no durable workflow. Retain the candidate, rationale, and reactivation conditions; no artifact.
- `merge`: the existing capability already covers the task and the new evidence does not justify a behavior change. Update provenance/decision history only; no duplicate Skill.
- `update`: the same capability needs a concrete workflow, trigger, verification, or authoritative-version correction. Name the target and supply the complete replacement artifact.
- `create`: a distinct repeatable capability passes every publication criterion. Supply the complete new artifact and target task-domain Plugin.

Never select `create` merely because the source changed. Never select `merge` or `update` based on name similarity alone.

## Rationale checklist

The rationale must state:

- which internal and external capability IDs were compared;
- the user-facing distinction or overlap;
- why the evidence is authoritative enough;
- why the outcome is preferable to not promote, merge, update, or create alternatives;
- how the artifact will be verified.
