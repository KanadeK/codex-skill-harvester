# Scale evolution roadmap

Volume is a capacity trigger, not a publication KPI. Every phase retains the same promotion quality gate.

## Phase A: scale foundation

- Version taxonomy and catalog classification.
- Normalize deletion-like terminology to `not_promoted`.
- Bound review batches and add continuation.
- Add stage-owned metrics, storage inventory, projections, and migration triggers.
- Keep the Git-native published catalog and artifacts unchanged; runtime lifecycle has moved to SQLite after the measured file-traversal bottleneck.

Exit: contracts validate, benchmark is reproducible, CI is green, and no broad scan was run.

## Current work package: high-throughput vertical slice

- Record the total-control route in `docs/plan-adoption-audit.md` after reconciling the untrusted external planning input with the merged scale foundation.
- Reserve `v0.2.0` without issuing it. A release needs a first vertical slice, one real calibration campaign, all gates, and a new total-control approval.
- Keep observations separate from normalized candidates; prove source-group/topic, five queues, L0–L3, SQL-bounded paging, runtime stop-loss, and source-level checkpoints in one exercised path.
- Run a structural three-group canary and automatic ramp to currently executable registered capacity. Keep the long-horizon 180–260 endpoint campaign gated on a real endpoint inventory and query-cursor implementation; the current inventory is not relabeled as that full campaign.

Exit: the next worker can implement one bounded slice from a single authority without treating projected volume, a green PR, or a foundation merge as a publication commitment.

## Phase B: larger SQLite-backed operation

Trigger: the endpoint inventory and query connector exist to make the 5–10% same-campaign canary meaningful.

- Add discovery-query topics and a round-robin cursor for each.
- Check all high-trust sources each cycle; rotate discovery topics under explicit source/review budgets.
- Calculate due-for-review from volatility and last authoritative review.
- Record review duration/token/cost only when an authoritative usage feed exists.
- Emit compact round summaries while retaining append-only records.

Exit: large queues are bounded, prioritized, resumable, and observable without changing storage authority.

## Phase C: concurrent local-first registry

Trigger: measured single-writer queue latency or campaign backlog exceeds the current SQLite execution envelope.

- Operate the existing SQLite authority; add worker claims only after measured concurrent-writer demand.
- Keep schemas, taxonomy, published Skills, evals, and review summaries in Git.
- Migrate in one validated write/swap slice with one runtime authority; do not retain side-by-side readers or writers.
- Add worker claims only if parallel writers are actually required and lease/recovery behavior is tested.

Exit: old and new backend fixtures produce equivalent cursors, pages, canonical ids, and decisions.

## Phase D: cold evidence and semantic retrieval

Trigger: evidence retention or comparison cost exceeds the SQLite/Git envelope.

- Partition cold evidence metadata by source and month in Parquet.
- Build a replaceable lexical/vector index over normalized fingerprints and evidence summaries.
- Use indexes for recall only; Codex retains semantic promotion authority.
- Measure false-merge and missed-near-duplicate rates before expanding automation.

Exit: derived indexes rebuild from authoritative records and quality evals remain above the approved threshold.

## Phase E: large published catalog

Trigger: hundreds or thousands of verified capabilities exist.

- Maintain small task-domain Plugins and curated Collections.
- Add searchable install metadata, variants, deprecation/successor links, and revalidation schedules.
- Never offer the complete catalog as one installation unit.
- Retain trigger evals, end-to-end behavior, provenance, and non-overlap evidence per Skill.

Exit: users find and install coherent task bundles without exposure to the evidence corpus.

## Decisions reserved for total control

- Authoritative model-usage/cost feed and budget.
- SQLite-only maintenance versus a service-backed queue after concurrency evidence exists.
- Quality thresholds for a semantic index or automated prioritizer.
- Distribution policy once multiple curated Collections are necessary.
