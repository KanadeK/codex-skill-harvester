# ADR-001: Defer indexed storage until a measured trigger

## Status

Accepted

## Date

2026-08-27

## Context

The strategic envelope reaches millions of source observations and hundreds of thousands of discoveries. The current repository has 110 candidates and uses one whole source-state JSON plus one file each for discovery, reviewed decision, and applied decision. This is simple now, but whole-state rewrites and hundreds of thousands of files will not remain economical.

Choosing SQLite, Parquet, or a hosted queue only from a projected upper bound would add migration and operational cost before the bottleneck exists.

## Decision

Retain Git-JSON as the active backend. Add a reproducible benchmark and machine-readable thresholds. Crossing any threshold requires a new migration ADR and measured comparison.

The default next hot-state backend is SQLite because the product is local-first and currently single-writer. Parquet is reserved for cold analytical evidence. A semantic index is derived and non-authoritative.

## Alternatives considered

### Migrate everything to SQLite now

Rejected because the corpus is tiny, Git review is useful, and no measured bottleneck justifies a new persistence layer.

### Commit sharded JSONL immediately

Deferred. JSONL reduces file count but makes individual review/update diffs and transactional replacement less direct. It may be an export format but does not solve indexing and queue access alone.

### Adopt a hosted database or queue

Rejected for this phase. It breaks local-first zero-service operation without evidence of a multi-writer requirement.

## Consequences

- Subsequent scans remain simple and compatible.
- Review must be bounded while status still enumerates records.
- There is an explicit point where remaining on JSON requires reevaluation.
- A future migration must preserve canonical ids, cursors, append-only decisions, and reproducible exports.
