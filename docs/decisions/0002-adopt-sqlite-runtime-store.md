# ADR-002: Adopt SQLite as the single runtime store

## Status

Accepted on 2026-08-29; implementation is limited to the first high-throughput vertical slice.

## Context

The active Git-JSON implementation has one complete `state/harvest-state.json`, plus one inbox, reviewed-decision, and applied-decision JSON file per candidate lifecycle. `sources.run_scan` rewrites the source state and inbox, `reporting` scans the candidate/decision directories, `decisions.apply_decision` reads/writes those records, and repository validation and the benchmark enumerate them. The measured benchmark required 524 seconds to parse/enumerate 30,000 synthetic lifecycle files on the reference Windows workspace.

This is an observed filesystem traversal and whole-state-rewrite bottleneck, not only a forecast. The product needs broad acquisition with a bounded, durable review queue. Continuing to add runtime JSON files would make each status, validation, review, and Git operation worse.

## Decision

Use the standard-library `sqlite3` module and one single-writer database at `state/harvest.sqlite3` as the authority for runtime source cursors, observations, query/semantic batches, Evidence Packs, normalized candidates, queue state, decision records, source utility, and run checkpoints. Schema 3 keeps these stages separate: evidence never enters a review queue merely because its source is official.

The database schema owns runtime state only. Git continues to own source definitions, taxonomy, capability catalog, original Skill and Plugin files, evaluation definitions/results, release assets, and readable run/migration manifests. SQLite receives no copied raw page bodies and no executable third-party script.

The cutover uses a one-time importer that writes a temporary database, validates counts and stable ids, and atomically installs it. It is not a compatibility path: after the cutover all runtime commands use SQLite; legacy JSON runtime paths are deleted in the same commit. A failed import leaves the current authority untouched. A later database format migration follows the same write-validate-swap protocol, never a long-lived dual write.

## Alternatives considered

### Keep Git-JSON and add more sharding

Rejected. It leaves the multi-file lifecycle and full directory traversal in the active path, the exact bottleneck already measured.

### SQLite with a permanent JSON fallback or dual writer

Rejected. Two writers or two readers create ambiguity over cursor, queue, and decision authority and conceal migration defects.

### SQLite for queue only

Rejected. Source state and candidate/decision lifecycle would still require full JSON enumeration and cross-store consistency.

### Parquet, embeddings, or a hosted queue now

Deferred. Cold analytical evidence, semantic recall, and multi-writer service coordination have not shown their own measured bottleneck. SQLite is sufficient for local-first, single-writer hot state.

## Consequences

- The first slice must update every runtime caller together: scanner, reporting, decision application, validation, benchmark, CLI, fixtures, and harvest workflow.
- The importer must prove source-state, observation, candidate, and decision id/count preservation before legacy deletion. A legacy discovery is always preserved as an observation; only a discovery with an existing reviewed decision becomes a migrated candidate.
- Queue paging and status aggregation execute in SQLite. Stable queue order, cursor predicates, and `LIMIT` use matching indexes; runtime callers do not load the full pending queue for pagination.
- Commands fail fast if the SQLite store is absent, malformed, or at an unsupported schema version; they must not silently read legacy JSON.
- A run report records which stages were measured, checkpoint/cursor state, source/observation/candidate/queue metrics, failures, and Usage `measured=false` when no authoritative meter is available.
- SQLite transaction handling uses explicit short transactions and parameterized queries. Connections are closed explicitly; no new dependency is introduced.
