# Plan adoption audit

**Status:** current execution authority for the high-throughput route.

**Baseline:** merged PR #6 at `6a54e7fc2748b02463fb269c7e9036f77812fae3`.

**Current work package:** PR #7 remains the open deterministic base. PR #8 was squash-merged into that branch at `d0cb9ef0d79ea254598fe66ee6f47a4dd0e532c3` before the 2026-08-30 correction began; it was not merged to `main`. `codex/pr8-campaign-corrections` now carries the completion-lifecycle and Python audit-gate corrections as a new stacked review boundary. No PR may merge to `main`, and no tag or Release may be created, without a later controller decision.

## What is confirmed now

- PR #6 is the scale-planning foundation; it is not the complete production line.
- SQLite schema 3 is the sole runtime authority. It has separate observations, query/semantic batches, Evidence Packs, candidates, five queues, decisions, source utility, and run checkpoints. There is no JSON fallback, dual read, or dual write.
- The current store preserves 462 observations, 117 Evidence Packs, and 113 reviewed candidates/decisions across 30 registered source cursors. PyPI package updates remain observations, not queue work. The current catalog has two internal Skills in two task-domain Plugins, and no candidate or semantic/query batch is pending.
- A candidate exists only after Codex reads the actual cached evidence as untrusted data and imports an Evidence Pack with one user goal, inputs/outputs, non-obvious decisions, authority/license/risk judgment, adjacent capabilities, and the complete seven-field fingerprint. `workflow_signal` is only an optional non-authoritative hint.
- Source trust and workflow authority are separate. An official registry or package feed may be authentic while remaining discovery-only. `official-gap` requires explicit operational workflow authority.
- The 21-query Domain × Intent Topic Bank, query cursors, source group/topic, Evidence Packs, fingerprints, L2 matches, and bounded L3 recalls are persisted on the real path. L3 is recall only; it cannot merge, update, create, reject, or publish.
- Scheduled and manual production harvest automation runs `campaign --ramp`; it cannot bypass canary, policy, checkpoints, or stop-loss with a bare scan.
- Review pagination and status counts execute in SQLite. Queue filters, stable ordering, cursor comparison, and `LIMIT` are database operations backed by matching indexes.

## Capacity direction, not production KPI

The first complete campaign is planned to exercise **180–260 endpoints, 1,500–3,000 actual queries, 80,000–250,000 observations, 4,000–12,000 normalized candidates, and 400–1,000 deep reviews**. For the explicitly authorized full-capacity exercise, 180 endpoints and 1,500 actual queries are the parent-campaign completion lower bound. Observation, candidate, deep-review, and Skill counts remain measured outcomes, not quotas or publication promises, and none may weaken evidence, originality, trigger, installation, or E2E gates.

There is no artificial output ceiling for qualified Skills. Every independently useful and fully validated Skill may enter a review PR. The earlier 30–90 estimate is neither a cap nor a quota. Zero published Skills can be the correct campaign result.

The first 5–10% of a complete campaign is its canary, not a separate small campaign. Healthy applicable metrics permit automatic ramp through the registered capacity. A stop-loss breach writes a checkpoint and retains every unprocessed source or candidate; it never converts unfinished work into `not_promoted`.

## Sole authority map

| Boundary | Sole authority |
| --- | --- |
| Registered source identity, trust, authority, license, adapter | `sources/registry.json` |
| Campaign source groups, topics, canary, queue order, workload/technical stop-loss | `config/campaign-policy.json` |
| Review page default and maximum | `config/scale-policy.json` |
| Runtime cursor, observation, query/semantic batch, Evidence Pack, candidate, queue, decision, checkpoint | `state/harvest.sqlite3` schema 3 |
| Canonical capability ids, facets, aliases, variants | `catalog/capabilities.json` and `catalog/taxonomy.json` |
| Published Skill, Plugin, eval, release history | Git-tracked `plugins/`, marketplace, `evals/`, and release reports |
| Runtime behavior | Tested code under `src/skill_harvester/` |

Reports summarize these authorities; a report never becomes a second state writer. Raw external bodies remain temporary and third-party scripts are never executed.

## Adopted product model

### Three layers

1. **Evidence/Discovery.** High-volume source responses become minimal observations containing provenance, revision, trust, license, source group, topic, facts, and L0/L1 identity. Raw bodies are not committed.
2. **Capability Registry.** Content-reviewed Evidence Packs may normalize observations into candidates. Candidates own the seven-field fingerprint, L2 structural matches, L3 recall, queue placement, decision history, aliases/variants, and reactivation conditions.
3. **Published Skills.** Only supervised, original, installable, trigger-safe, E2E-verified artifacts are published. Users install small task-domain Plugins or Collections, not the evidence corpus or a giant universal bundle.

### Dual-speed funnel

```text
cheap bounded acquisition
    -> observation + source cursor
    -> persisted semantic batch + Codex Evidence Pack
    -> candidate + L2/L3 recall + five queues
    -> supervised L4 semantic decision
    -> evidence pack / synthesis / eval / install / E2E / originality
    -> review PR
    -> controller decides merge and release
```

Acquisition and normalization may run broadly. Expensive comparison, synthesis, and validation continuously consume the five priority queues within policy. A large evidence backlog is normal and is not a candidate backlog.

### T0–T4 sources

- **T0:** format and protocol authority.
- **T1:** official operational documentation, CLI, OpenAPI, releases, changelogs, RSS, and sitemaps.
- **T2:** primary project repositories and maintainers.
- **T3:** representative implementations used for comparison.
- **T4:** community directories, discussions, registries, and search results used as discovery or demand signals.

Package registries are early discovery signals. Their official status proves feed provenance, not an operational workflow or a new user-facing tool.

### Classification

Planning uses `Domain × Intent + Topic Bank`. Published and candidate classification remains one stable primary capability family plus versioned multidimensional facets: domain, intent, inputs, outputs, tools/platforms, side effects/risk, volatility, maturity, and trust. Evidence may add facet values through a versioned taxonomy change; coverage is not forced into a rigid directory tree.

### Five queues

Queue precedence is:

1. `urgent-impact` — verified evidence affects a published capability.
2. `official-gap` — explicit official operational workflow evidence has no resolved capability decision.
3. `reactivation` — a retained decision's executable reactivation condition is met.
4. `novel-discovery` — a normalized candidate with no stronger condition.
5. `aged-backlog` — deliberately deferred normalized work.

Queue placement occurs only after normalization. Trust alone cannot enqueue an observation.

### L0–L4 comparison

- **L0:** stable source item plus revision identity.
- **L1:** exact evidence hash.
- **L2:** exact normalized seven-field fingerprint lookup.
- **L3:** deterministic bounded recall against the capability catalog.
- **L4:** supervised semantic adjudication of duplicate, update, variant, merge, distinct, or uncertain.

L2 and L3 are auditable evidence. Neither is an automatic semantic decision, and a future vector index remains derived and rebuildable.

## Runtime stop-loss and checkpoints

Before each next source request, and again after each successful source checkpoint, the campaign enforces the policy-owned limits for:

- source requests;
- cumulative downloaded bytes;
- runtime SQLite bytes;
- observed work items;
- normalized candidates; and
- L3 recall work.

The campaign also records the 100-credit boundary, but Usage remains `{"measured": false}` until an authoritative campaign-scoped meter exists. No credits may be bought and auto top-up must remain disabled. Missing measurement is never replaced with an estimate.

Canary failures and ramp failures both produce campaign reports. Earlier successful sources retain their cursor and records because campaign execution checkpoints one source at a time. Pending source ids remain explicit. Unexecuted L4/deep-review stages use `{"measured": false}` rather than a fabricated zero.

### Current content-production result

The validator-rebuildable [full campaign report](../runs/2026-08-30-full-content-production.json) records the current authority. The executable inventory is 204 revision-pinned endpoints. All 1,622 unique Topic Bank queries completed in 1,626 attempts, with four recoverable GitHub rate-limit failures, 151 discovery hits, and no pending query. The final full-inventory ramp made 204 successful source requests, downloaded 517,498 bytes, inserted 116 changed observations, and had zero source failures. The SQLite authority totals 1,204 observations.

Across eight resumable batches, Codex reviewed 217 observations, produced 58 Evidence Packs, normalized 26 candidates, received 263 bounded L3 recalls, and performed 26 measured L4 adjudications: seven creates, three updates, one merge, and 15 `not_promoted`. Thirty-two Evidence Packs were stopped before candidate promotion. The Git catalog now contains eight Skills; the campaign-created set covers Python and npm package readiness, Ansible collection validation, Cargo build performance, CORS diagnosis, curl request auditing, and offline Git transfer. GitHub release evidence received reviewed updates, including release-tag binding for asset attestations. Query rotation, semantic export, and a stable official OpenAI source all produced real no-op replays; pending query, semantic, and L4 counts are zero.

The parent campaign is `campaign_completed` because 204/180 endpoints and 1,622/1,500 actual queries satisfy the explicit policy-owned capacity objective. No Skill count contributed to completion, no stop-loss was triggered, Usage credits and semantic-review tokens remain `measured=false`, and no Release was published. The earlier [first-slice report](../runs/2026-08-29-content-production.json) remains immutable historical evidence rather than current campaign status.

## Migration decision and deletion condition

The active upgrade route is one-way:

1. read the v0.1.1 Git-JSON source state, discovery inbox, and reviewed decisions;
2. create a temporary final-schema SQLite database;
3. preserve every legacy discovery as an observation;
4. create migrated candidates only for records that already have a reviewed decision;
5. validate source-state, observation, candidate, decision counts and stable ids;
6. atomically replace the destination; and
7. delete legacy runtime JSON from the active tree.

PR #7 was not merged when schema 1's conflation was found, so schema 1 receives no permanent reader, shim, flag, or dual-write transition. Git history is the rollback surface. The temporary PR-only conversion preserved the 110 reviewed records and reclassified its 209 unreviewed records as observations.

## Adoption ledger for the Pro plan

| Area | Decision | Reason and entry/deletion condition |
| --- | --- | --- |
| Three layers and million-scale evidence envelope | **adopted** | It separates evidence volume from publication quality. Counts remain capacity envelopes. |
| T0–T4 source tiers | **adopted, modified** | Vocabulary is adopted; current registry fields remain authoritative until one exercised schema migration replaces them. |
| Domain × Intent + Topic Bank | **adopted, modified** | Used for source rotation and planning; the versioned facet taxonomy remains publication authority. |
| Five queues | **adopted** | Implemented only after candidate normalization, with policy-owned precedence and bounded SQL paging. |
| L0–L4 | **adopted** | L0–L3 are deterministic pipeline evidence; L4 stays supervised. Quality rates wait for a labeled set. |
| Candidate/artifact/capability lifecycle | **adopted** | Observation and candidate are now distinct; artifact and capability remain Git-reviewed lifecycles. |
| Evidence Pack through install/E2E/originality | **adopted** | These remain mandatory publication gates; they are not bypassed by throughput. |
| Plugins/Collections by installation intent | **adopted** | Product grouping follows user task domains, never source websites. |
| Reverse evidence impact | **adopted, minimal** | `published_impact` now prioritizes content-reviewed evidence into `urgent-impact`; a multi-capability reverse graph remains deferred until real fan-out appears. |
| HTTP/RSS/GitHub/OpenAPI/sitemap connector expansion | **modified and incremental** | Add one connector only for a selected source group with fixtures, cursor semantics, stop-loss, and no-op proof. No empty connector framework. |
| Package registries as early authorities | **rejected** | They remain discovery signals until separate operational workflow evidence exists. |
| Git-JSON → SQLite → Parquet → semantic index | **adopted as measured evolution** | SQLite is active hot-state authority. Parquet needs measured cold-analysis pressure; a semantic index needs labeled recall evidence and must be rebuildable. |
| Storage interface, dual read/write, compatibility shim, feature flag | **rejected for this cutover** | They would create multiple truths. Introduce a transition only when an approved future migration genuinely requires it, with an explicit deletion condition. |
| Multi-worker leases/service queue | **deferred** | Requires measured single-writer contention and a recovery/ownership design. |
| Numeric recall/false-merge claims | **deferred** | No quality number is valid before a versioned labeled set and recorded adjudication method. |
| 3,000-query one-shot sweep | **modified** | Queries rotate within a resumable complete campaign; canary and stop-loss govern ramp. |
| Automatic semantic merge | **rejected** | L4 remains supervised during at least the first three campaigns and until separately approved. |
| Automatic Release | **deferred** | Consider only after at least three stable campaigns and a later explicit decision. |
| Count inflation, publication quotas, and unmeasured zeroes | **rejected** | They obscure actual funnel quality and stage ownership. |
| Prebuilding an entire proposed module tree | **rejected** | Only exercised boundaries may create modules or schemas; unused abstractions are removed. |

## Model, risk, and release policy

- Luna performs high-throughput routing, extraction, and initial triage only.
- Terra performs ordinary semantic comparisons and implementation.
- Sol is reserved for difficult/high-impact adjudication and final audit.
- Medical, legal, financial, real-world control, credential-heavy, and other high-risk domains may accumulate evidence in phase one but automatic publication is blocked. Publication requires explicit user and controller approval.
- The first three campaigns may open PRs; the controller decides every merge and release. Semantic merge is not unattended.
- `v0.2.0` is the current manual release candidate. The required vertical slice and calibrated campaign are complete, and the user has explicitly approved release after all local and remote gates pass. This is one bounded authorization, not approval for future automatic Releases.

## 0–30 day mainline

1. Submit the full-campaign stacked PR after complete local gates and dual-platform CI; keep the existing stack and new PR unmerged until controller review.
2. Build a small versioned labeled set before publishing recall, false-merge, or semantic quality rates.
3. Expand executable inventory toward the campaign capacity range one connector/source slice at a time. Canary remains 5–10% of the same complete inventory.
4. Run the complete campaign within existing credits and infrastructure. Retain every cursor and unresolved candidate; do not force a Skill count.
5. Report measured throughput, failures, candidate yield, L3 recall work, deep-review work, validation yield, and bottlenecks. The controller selects the next narrow repair or expansion slice.

## Current unknowns and measured entry conditions

- **Unknown:** campaign-scoped credit usage is not authoritatively observable. Keep `measured=false`.
- **Unknown:** labeled L3 recall and false-merge quality. Do not state percentages before adjudicated fixtures exist.
- **Measured once:** one 204-endpoint full-inventory ramp completed with 204 successes and no source failure. Do not extrapolate that single run to every source mix, endpoint count, or future campaign.
- **Parquet entry:** measured cold evidence size or analytical query cost exceeds SQLite/Git expectations.
- **Semantic-index entry:** labeled recall shows deterministic L3 is insufficient at the measured catalog size.
- **Multi-worker entry:** measured single-writer backlog or latency prevents the campaign target and recovery semantics are specified.
- **Automatic Release entry:** at least three stable campaigns plus explicit controller and user approval.

## Reserved decisions

PR #7 has merged. The user has authorized a current-main integration of the reviewed content-production tree and one manual `v0.2.0` release after all gates pass; the superseded stacked PR is not merged independently. The controller still decides future campaign stop-loss or budget policy, semantic quality thresholds, any new storage migration, multi-worker operation, high-risk publication, and Release automation. A green test suite or campaign report remains evidence rather than authority outside this explicitly approved release.
