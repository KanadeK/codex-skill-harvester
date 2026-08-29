# Scale evolution roadmap

Volume is a capacity trigger, not a publication KPI. Every phase retains the same promotion quality gate.

## Phase A: scale foundation

- Version taxonomy and catalog classification.
- Normalize deletion-like terminology to `not_promoted`.
- Bound review batches and add continuation.
- Add stage-owned metrics, storage inventory, projections, and migration triggers.
- Keep Git-JSON and runtime dependencies unchanged.

Exit: contracts validate, benchmark is reproducible, CI is green, and no broad scan was run.

## Phase B: larger Git-native operation

Trigger: queue growth is material but below storage thresholds.

- Add discovery-query topics and a round-robin cursor for each.
- Check all high-trust sources each cycle; rotate discovery topics under explicit source/review budgets.
- Calculate due-for-review from volatility and last authoritative review.
- Record review duration/token/cost only when an authoritative usage feed exists.
- Emit compact round summaries while retaining append-only records.

Exit: large queues are bounded, prioritized, resumable, and observable without changing storage authority.

## Phase C: indexed local-first registry

Trigger: a policy threshold is crossed and a benchmark confirms file traversal or whole-state rewrites are limiting.

- Migrate cursors, hashes, queue, capability links, aliases, and decision indexes to SQLite.
- Keep schemas, taxonomy, published Skills, evals, and review summaries in Git.
- Provide deterministic import/export and side-by-side validation.
- Add worker claims only if parallel writers are actually required.

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
