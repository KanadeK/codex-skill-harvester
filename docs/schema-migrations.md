# Schema and taxonomy migrations

## Version contracts

- Every durable JSON document has an integer `schema_version`.
- Capability records also name the semantic `taxonomy_version`.
- Readers accept only versions they explicitly implement. A future version fails fast.
- Append-only evidence and decision history is not rewritten merely to update terminology.

## Current compatibility

| Record | Legacy | Current | Read behavior |
| --- | --- | --- | --- |
| Catalog | schema 1 | schema 2 + taxonomy 1.0.0 | schema 1 migrates only with an explicit classification map; schema 2 validates directly |
| Reviewed decision | schema 1 | schema 2 | schema 1 `discard` is interpreted as `not_promoted`; schema 2 uses `not_promoted` and requires reactivation conditions |
| Applied decision record | schema 1 | schema 2 | both remain readable; legacy files stay byte-preserved |
| Runtime source state/discovery/decision/checkpoint | Git-JSON schema 1 | SQLite runtime schema 3 | every discovery imports as an observation; only reviewed records receive Evidence Packs and candidates; content/query batches and explicit query cycles use schema 3; no runtime JSON or older-SQLite reader after cutover |

## Migration protocol

1. Freeze the affected writer and record counts, versions, and last successful cursor.
2. Validate every input against its declared old schema.
3. Write deterministic output to a temporary destination, never in place.
4. Require explicit mappings for semantic facts code cannot infer, including family and facets.
5. Validate output counts, canonical ids, references, and new schema.
6. Run migration again; current-version input must be a no-op.
7. Atomically replace the active manifest/store only after every check passes.
8. Preserve the migration manifest and append-only history through the rollback window.

For the completed JSON-to-SQLite cutover, the importer writes a temporary schema-3 database and swaps it only after source-state, observation, Evidence Pack, candidate, decision, and stable-id validation; legacy JSON is then removed from the active tree. Query state stores the last completed cycle and continuation cursor, so a later cycle resumes discovery without replaying completed work inside the earlier cycle. PR #7's unmerged intermediate schemas were replaced rather than supported by a compatibility path. A later SQLite migration writes a new database and swaps it after validation. Parquet migrations write versioned partitions before changing their manifest.

## Legacy non-promotion semantics

The token `discard` in schema-1 decision files remains for historical integrity. Operator-facing readers normalize it to `not_promoted`. Its rationale and sources remain authoritative. The default legacy reactivation rule is:

> Reconsider only when new authoritative evidence establishes a repeatable task with clear inputs, outputs, non-obvious decisions, verification, and a capability boundary not already covered by the catalog.

Any more specific condition in the rationale takes precedence. Schema-2 non-promotion decisions must store `reactivation_conditions` explicitly.

## Canonical identity migrations

Canonical ids never change during taxonomy or Plugin reorganization. A rename adds an alias. A consolidation marks old ids as merged into the survivor. A split creates new ids and records their origin; it does not repurpose the old id with a different goal.
