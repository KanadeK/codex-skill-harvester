# Reviewed decision contract

Read this only when a changed-source discovery has survived the initial usefulness and provenance review.

## Required fields

```json
{
  "schema_version": 1,
  "candidate_id": "stable-discovery-id",
  "reviewed_by": "codex",
  "reviewed_at": "RFC-3339 timestamp",
  "outcome": "discard|merge|update|create",
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

For `create` and `update`, replace `artifact: null` with an object containing `"origin": "original-synthesis"`, the target Plugin ID and complete manifest, Skill name, original `SKILL.md` text, optional original reference files, and optional original scripts. Every artifact file path must be relative, remain inside the selected Skill directory, and have no executable source copied from public material.

## Outcome rules

- `discard`: unsuitable, unverifiable, exact duplicate, or no durable workflow. Record why; no artifact.
- `merge`: the existing capability already covers the task and the new evidence does not justify a behavior change. Update provenance/decision history only; no duplicate Skill.
- `update`: the same capability needs a concrete workflow, trigger, verification, or authoritative-version correction. Name the target and supply the complete replacement artifact.
- `create`: a distinct repeatable capability passes every publication criterion. Supply the complete new artifact and target task-domain Plugin.

Never select `create` merely because the source changed. Never select `merge` or `update` based on name similarity alone.

## Rationale checklist

The rationale must state:

- which internal and external capability IDs were compared;
- the user-facing distinction or overlap;
- why the evidence is authoritative enough;
- why the outcome is preferable to discard, merge, update, or create alternatives;
- how the artifact will be verified.
