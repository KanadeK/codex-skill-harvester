# Scale evolution roadmap

Volume is a capacity trigger, not a publication KPI. Every phase retains the same promotion quality gate.

## Phase A: scale foundation

- Version taxonomy and catalog classification.
- Normalize deletion-like terminology to `not_promoted`.
- Bound review batches and add continuation.
- Add stage-owned metrics, storage inventory, projections, and migration triggers.
- Keep the Git-native published catalog and artifacts unchanged; runtime lifecycle has moved to SQLite after the measured file-traversal bottleneck.

Exit: contracts validate, benchmark is reproducible, CI is green, and no broad scan was run.

## Current work package: content-driven production slice

- Keep PR #7 as the deterministic stacked base and reserve `v0.2.0` without issuing it.
- Persist content/query work in SQLite schema 3, make source-level workflow hints non-authoritative, and require Codex-reviewed Evidence Packs before candidate creation.
- Exercise 21 Domain × Intent queries, 26 executable endpoints, resumable failures, three semantic batches, L2/L3, L4, original synthesis, evals, and no-op replay in one real slice.
- Submit one new Python package-delivery Skill and one GitHub release-evidence update for review. PR #8 was later squash-merged only into the still-open PR #7 branch; nothing reached `main` and no Release was published.

Exit: the slice is reviewable with code-generated metrics, all local/remote gates, and zero pending query, semantic, or candidate work. That makes the slice `complete`, while the parent remains `active` below its policy-owned 180-endpoint/1,500-query lower bound. Observation/candidate/Skill ranges remain capacity direction, not output quotas.

## Phase B: larger SQLite-backed operation

Trigger: the current 26-endpoint/21-query slice remains stable, its stacked change is accepted in the approved merge order, and a new explicit campaign cycle is opened. Ordinary inventory expansion inside the existing stop-loss policy does not require a separate volume approval.

- Expand the existing Topic Bank and persisted query batches from measured source utility; do not replay completed queries inside one cycle, and start each later explicit cycle from its saved continuation cursor.
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
