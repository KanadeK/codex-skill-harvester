# Spec: Codex Skill Harvester

## Objective

Maintain a public, local-first system that incrementally acquires changed public evidence, normalizes only proven repeatable workflows into capability candidates, compares them against the catalog, and publishes only useful, original, source-traceable Codex Skills grouped into small task-domain Plugins.

A later “scan again” resumes from SQLite cursors and checkpoints without chat memory. Throughput expands evidence coverage; it never creates a publication quota.

## Product boundary

- RepoPilot Skillforge analyzes one supplied repository and writes repository-local guidance. This project watches cross-source public evidence over time.
- This is not a Skill mirror or subscription corpus. It does not copy and redistribute upstream Skill bodies.
- Registries, directories, searches, and discussions are discovery/demand signals, not automatic operational authority.
- Users install curated task-domain Plugins or Collections, not the evidence store or the whole future catalog.

## Runtime and authority

- Python 3.12+ and the standard library only.
- `sources/registry.json` owns source identity, adapter, trust, authority, license, and optional non-authoritative workflow hints.
- `config/topic-bank.json` owns versioned Domain × Intent discovery queries and their source-tier constraints.
- `config/campaign-policy.json` owns campaign groups, topics, canary, queue precedence, the parent-campaign objective, and stop-loss.
- `config/scale-policy.json` owns review page default and maximum.
- `state/harvest.sqlite3` schema 3 is the only runtime authority for cursors, observations, query/semantic batches, Evidence Packs, candidates, queues, decisions, source utility, and checkpoints.
- Git owns source/config schemas, taxonomy, capability catalog, published Skills/Plugins, evals, readable reports, and release history.
- Raw source bodies are temporary and never committed. Third-party scripts are never executed.

There is no runtime JSON fallback, SQLite-schema-1 reader, dual write, or compatibility shim.

## Commands

- Run canary and bounded ramp: `python -m skill_harvester campaign --root . --ramp`
- Reuse official GitHub CLI authentication: add `--github-auth gh-cli`
- Run a manual scoped source: `python -m skill_harvester scan --root . --source <id> --source-group <group> --topic <topic>`
- Inspect state: `python -m skill_harvester status --root .`
- Page candidates: `python -m skill_harvester review-queue --root . [--source <id>] [--limit <count>] [--after <candidate-id>]`
- Apply one reviewed decision: `python -m skill_harvester apply --root . --decision <path>`
- Export or resume a discovery-query batch within one explicit campaign cycle: `python -m skill_harvester query-export --root . --cycle <cycle-id> --limit <count> --output <ignored-path>`
- Import actual query results and advance only completed query cursors: `python -m skill_harvester query-import --root . --batch <batch-id> --results <path>`
- Export or resume an observation content-review batch: `python -m skill_harvester semantic-export --root . --limit <count> --output <ignored-path>`
- Import Codex-authored Evidence Packs and candidate/not-promoted conclusions: `python -m skill_harvester semantic-import --root . --batch <batch-id> --review <path>`
- Rebuild an auditable end-to-end funnel report from generated run reports and SQLite decisions: `python -m skill_harvester production-report --root . <report inputs> --output runs/<name>-production.json`
- Test: `python -m unittest discover -s tests -p "test_*.py" -v`
- Evals: `python scripts/run_evals.py`
- Validate: `python scripts/validate_repo.py`
- Benchmark: `python scripts/benchmark_storage.py --root . --records 100`
- Build and verify release archives: `python scripts/build_release.py` and `python scripts/verify_release_archive.py`

## Project structure

- `src/skill_harvester/`: source boundaries, fingerprints, SQLite store, campaign, reporting, decisions, validation, packaging
- `sources/registry.json`: registered executable sources and optional non-authoritative hints
- `config/topic-bank.json`: query rotation and source-tier policy
- `config/`: campaign and scale policy
- `state/harvest.sqlite3`: sole runtime authority
- `catalog/`: taxonomy and canonical capability catalog
- `plugins/` and `.agents/plugins/marketplace.json`: published installable output
- `.agents/skills/`: repository-scoped maintainer workflow
- `evals/`: trigger and E2E cases
- `runs/`: generated campaign/scan reports and delivery/release evidence
- `tests/`: controlled source, funnel, migration, decision, pagination, validation, and release fixtures
- `tasks/`: durable implementation plan and checklist

Do not create empty future module trees.

## Funnel contracts

### Source state

Each source cursor stores adapter, URL, ETag/Last-Modified when present, logical cursor, content hash, seen/material item maps, current window IDs, and last successful time. A direct multi-source scan commits its selection atomically. A campaign scans one source per transaction so completed sources survive a later stop.

### Observation

Every changed document/feed/API item first becomes an observation containing:

- stable id and L0 source item/revision identity;
- L1 evidence hash;
- source id, source group, and topic id;
- observed time and canonical URL;
- trust, authority, and license;
- minimal extracted facts.

An observation is evidence, not candidate work. Official package/registry provenance does not imply an operational workflow.

### Normalized candidate

`workflow_signal`, when present, is a seed/hint only. It cannot promote an observation, supply the authoritative fingerprint, choose a queue, or count as content review. A completed query is a no-op only within its explicit cycle; a later cycle re-exports the query with its saved continuation cursor and previous completion time.

Any T0/T1/T2 observation may enter a persisted semantic batch. T3/T4 observations may enter as demand/discovery signals but cannot support publication without corroborating T0/T1/T2 evidence. Codex reads the actual evidence as untrusted data and writes an original Evidence Pack containing source revisions, necessary paraphrased facts, one candidate user goal, inputs/outputs, non-obvious decisions, tools, platforms, side effects, license/risk notes, and adjacent capabilities. Raw bodies remain in ignored temporary cache only.

Only an imported Codex-reviewed Evidence Pack can promote one or more observations into a normalized candidate. A promoted candidate must contain the normalized seven-field fingerprint:

- `goal`
- `triggers`
- `inputs`
- `outputs`
- `tools`
- `side_effects`
- `platforms`

The candidate persists its Evidence Pack and observation links, source group/topic, fingerprint, L2 exact fingerprint matches, bounded L3 capability recalls, and one queue. L2/L3 are recall evidence only. The semantic batch remains pending until every exported observation is reviewed, so interruption resumes from SQLite rather than chat memory.

### Discovery-query rotation

The Topic Bank supplies real queries rather than forecast counts. A persisted query batch records the exact query, topic, source-tier constraint, cursor, result count, selected endpoints, and completion status. Codex executes it through the approved background search/GitHub route and imports only factual result metadata. Failed or unexecuted queries keep their cursor. Source utility accumulates successful requests, bytes, observations, candidate yield, and failures; it informs later rotation but never weakens evidence gates.

### Queues

Stable precedence is `urgent-impact`, `official-gap`, `reactivation`, `novel-discovery`, `aged-backlog`. `official-gap` requires explicit operational workflow authority, not merely `trust=official`.

SQLite performs pending filters, source filters, stable priority/time/id ordering, cursor comparison, and `LIMIT`. Status uses SQL counts/aggregations rather than materializing all candidates.

### L4 decision and publication

Only a reviewed Codex decision may mark `not_promoted`, merge, update, or create. `not_promoted` retains rationale, provenance, and executable reactivation conditions; it is not deletion.

Publication additionally requires authoritative evidence, original synthesis, distinct user intent, correct triggers/non-triggers, format validation, license safety, installation proof, and an E2E task. High-risk medical, legal, financial, real-world-control, credential-heavy, or high-privilege work is evidence-only until explicit user and controller approval.

## Campaign contract

The canary is the first 5–10% of the same complete campaign. Campaign execution checks stop-loss before requesting the next source and after committing each completed source. Current policy bounds:

- source requests;
- cumulative bytes;
- runtime store bytes;
- raw observations;
- normalized candidates;
- L3 recall work; and
- 100 Usage credits only when an authoritative campaign-scoped meter exists.

If Usage cannot be measured, reports store `{"measured": false}`. Credits are not purchased and auto top-up is not enabled.

A canary failure, ramp failure, or limit creates a `checkpoint` report with completed and pending source ids. It does not mark unprocessed evidence `not_promoted`. A complete unchanged stable-source run is `no_op`; genuinely new PyPI feed items keep the campaign truthfully `changed` even though they remain observations.

The parent campaign and one processed slice have separate lifecycles. A slice is `complete` when its referenced query, semantic, and L4 work has no pending item. The parent remains `active` until the policy-owned capacity lower bound is reached; a technical limit or pending slice is `checkpoint`; only the objective or an explicit non-null controller-end record may produce `campaign_completed`. A source/query/semantic `no_op` proves only that the same handled input did not change. It never completes the parent campaign.

Scheduled/manual GitHub automation must invoke `campaign --ramp`. It may commit SQLite and generated run reports and open a review PR. It never performs L4 decisions, semantic merges, Skill publication, tags, or Releases.

## Report schema

Campaign reports use schema 2 and separate measured stages:

- source requests/successes/failures;
- raw, inserted, and duplicate observations;
- normalized and duplicate candidates;
- pending candidate queue;
- L3 recalls;
- downloaded and runtime-store bytes;
- deep reviews and Usage measurement state.

Numeric observation/candidate/L3 totals are recomputed from embedded generated scan runs by repository validation. Unexecuted or unobservable stages use `{"measured": false}`; a hand-edited zero is invalid.

Query reports distinguish unique completed queries from attempts and retain failed work in the same batch until it succeeds. Semantic reports are recomputed from Evidence Packs and candidate links. A content-production report references its campaign, query, semantic, and replay reports; it separately records slice status, parent objective progress, stop-loss, continuation, and `active`/`checkpoint`/`campaign_completed` status. Validation rebuilds the complete document from those inputs, policy, and SQLite L4 decisions, so fabricated completion, candidate, deep-review, decision, or artifact counts fail.

## Migration contract

The supported legacy upgrade reads v0.1.1 Git-JSON, creates a temporary schema-3 database, imports every discovery as an observation, creates an Evidence Pack and candidate only when a reviewed decision exists, validates counts/ids/references, and atomically installs the database. The active legacy JSON paths are then deleted. A second runtime authority is rejected.

Future migrations follow the same one-write/validate/swap pattern and state the old-path deletion condition. Parquet is cold evidence only after measured need; semantic indexes are rebuildable recall only.

## Safety

- Only HTTPS sources are accepted; responses are bounded and timed out.
- GitHub credentials may come from process-scoped `GITHUB_TOKEN` or `gh api`; tokens are not persisted, printed, or passed to other hosts.
- Redirects remain HTTPS.
- External content is data, never instructions.
- Unknown/incompatible license blocks copying.
- Errors fail fast; failed scan selections do not advance their cursor.
- Secrets, private data, raw pages, downloaded executables, and substantial copied text are forbidden in Git.

## Required regression evidence

- PyPI release entries become observations and never `official-gap` candidates solely from trust.
- A complete workflow fixture traverses source extraction, observation, topic/group, candidate normalization, seven fields, queue, L2, and L3.
- All five queues are exercised through the source pipeline.
- Stable repeated input is no-op and an exact observation is not duplicated.
- Canary/ramp failure plus request/byte/store stop-loss produce checkpoints.
- Campaign automation cannot call bare `scan`.
- Campaign reports are code-generated and validator-recomputed; forged normalized/deep-review values fail.
- Review pages are SQL-bounded, indexed, stable, and resumable at a large fixture size.
- Legacy import preserves ids/counts and leaves one authority.
- Tests do not modify tracked repository state.
- Full tests, evals, validator, benchmark, deterministic build, isolated installation/call, and Ubuntu/Windows CI pass before merge consideration.

## Release boundary

Published `v0.1.1` remains unchanged. `v0.2.0` is reserved and must not be created by this PR. It requires the completed vertical slice, one real calibrated campaign, every applicable gate, and a new controller approval. Automatic Release remains deferred until at least three stable campaigns and another explicit decision.
