# Plan adoption audit

**Status:** current execution authority for the high-throughput route.

**Baseline:** merged PR #6 at `6a54e7fc2748b02463fb269c7e9036f77812fae3`.

**Current work package:** PR #7 repairs and proves one observation-to-candidate vertical slice. It must not merge, tag, release, perform L4 semantic merges, or publish Skills without a later controller decision.

## What is confirmed now

- PR #6 is the scale-planning foundation; it is not the complete production line.
- SQLite schema 2 is the sole runtime authority. It has separate `observations` and `candidates` tables plus source cursors, candidate queues, decisions, and run checkpoints. There is no JSON fallback, dual read, or dual write.
- The schema-2 conversion preserved 319 observations and 110 reviewed candidates/decisions. The former 209 pending `discoveries` were retained as evidence: 200 PyPI package updates and nine later Codex release entries were not candidate queue work. The corrected live campaign then added 100 newer PyPI observations, so the current store has 419 observations, 110 reviewed candidates, and no pending candidate. No `not_promoted` records were fabricated to clear evidence.
- A candidate exists only after an explicit workflow-signal normalization step produces one user goal, clear inputs and outputs, and the complete seven-field fingerprint: `goal`, `triggers`, `inputs`, `outputs`, `tools`, `side_effects`, and `platforms`.
- Source trust and workflow authority are separate. An official registry or package feed may be authentic while remaining discovery-only. `official-gap` requires explicit operational workflow authority.
- Topic, source group, fingerprint, L2 matches, and bounded L3 recalls are persisted on the real scan path. L3 is recall only; it cannot merge, update, create, reject, or publish.
- Scheduled and manual production harvest automation runs `campaign --ramp`; it cannot bypass canary, policy, checkpoints, or stop-loss with a bare scan.
- Review pagination and status counts execute in SQLite. Queue filters, stable ordering, cursor comparison, and `LIMIT` are database operations backed by matching indexes.

## Capacity direction, not production KPI

The first complete campaign is planned to exercise **180–260 endpoints, 1,500–3,000 actual queries, 80,000–250,000 observations, 4,000–12,000 normalized candidates, and 400–1,000 deep reviews**. These are capacity and observation ranges. They are not minimum counts, publication promises, or a reason to weaken evidence, originality, trigger, installation, or E2E gates.

There is no artificial output ceiling for qualified Skills. Every independently useful and fully validated Skill may enter a review PR. The earlier 30–90 estimate is neither a cap nor a quota. Zero published Skills can be the correct campaign result.

The first 5–10% of a complete campaign is its canary, not a separate small campaign. Healthy applicable metrics permit automatic ramp through the registered capacity. A stop-loss breach writes a checkpoint and retains every unprocessed source or candidate; it never converts unfinished work into `not_promoted`.

## Sole authority map

| Boundary | Sole authority |
| --- | --- |
| Registered source identity, trust, authority, license, adapter | `sources/registry.json` |
| Campaign source groups, topics, canary, queue order, workload/technical stop-loss | `config/campaign-policy.json` |
| Review page default and maximum | `config/scale-policy.json` |
| Runtime cursor, observation, candidate, queue, decision, checkpoint | `state/harvest.sqlite3` schema 2 |
| Canonical capability ids, facets, aliases, variants | `catalog/capabilities.json` and `catalog/taxonomy.json` |
| Published Skill, Plugin, eval, release history | Git-tracked `plugins/`, marketplace, `evals/`, and release reports |
| Runtime behavior | Tested code under `src/skill_harvester/` |

Reports summarize these authorities; a report never becomes a second state writer. Raw external bodies remain temporary and third-party scripts are never executed.

## Adopted product model

### Three layers

1. **Evidence/Discovery.** High-volume source responses become minimal observations containing provenance, revision, trust, license, source group, topic, facts, and L0/L1 identity. Raw bodies are not committed.
2. **Capability Registry.** Explicit workflow signals may normalize observations into candidates. Candidates own the seven-field fingerprint, L2 structural matches, L3 recall, queue placement, decision history, aliases/variants, and reactivation conditions.
3. **Published Skills.** Only supervised, original, installable, trigger-safe, E2E-verified artifacts are published. Users install small task-domain Plugins or Collections, not the evidence corpus or a giant universal bundle.

### Dual-speed funnel

```text
cheap bounded acquisition
    -> observation + source cursor
    -> explicit workflow-signal normalization
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

### Corrected live calibration result

The code-generated `2026-08-29T13-55-27.992601Z` campaign completed its three-source canary and all 10 currently executable policy endpoints. It made 10 requests with a 100% source success rate, downloaded 363,165 bytes, and inserted 100 observations from the changing PyPI feed. It normalized zero candidates, produced zero L3 recalls, left zero pending candidates, and performed no deep review. Deep review and Usage are both `measured=false`; there were zero source failures. This is a truthful evidence-only yield, not a failed Skill-production target and not the full 180–260 endpoint campaign.

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
| Reverse evidence impact | **deferred** | Implement when real campaigns show one evidence change affecting multiple published capabilities. Delete any prototype that cannot trace to exercised lineage. |
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
- `v0.2.0` is reserved but not released. It requires this vertical slice, a real calibrated campaign, all gates, and a fresh controller approval. This PR does not meet that release authority by itself.

## 0–30 day mainline

1. Complete PR #7's observation/candidate repair, SQL paging, campaign automation, runtime stop-loss, unified reports, fixtures, real canary/ramp, and dual-platform CI.
2. Build a small versioned labeled set before publishing recall, false-merge, or semantic quality rates.
3. Expand executable inventory toward the campaign capacity range one connector/source slice at a time. Canary remains 5–10% of the same complete inventory.
4. Run the complete campaign within existing credits and infrastructure. Retain every cursor and unresolved candidate; do not force a Skill count.
5. Report measured throughput, failures, candidate yield, L3 recall work, deep-review work, validation yield, and bottlenecks. The controller selects the next narrow repair or expansion slice.

## Current unknowns and measured entry conditions

- **Unknown:** campaign-scoped credit usage is not authoritatively observable. Keep `measured=false`.
- **Unknown:** labeled L3 recall and false-merge quality. Do not state percentages before adjudicated fixtures exist.
- **Unknown:** throughput at 180–260 endpoints. The current registered inventory is smaller; do not extrapolate its latency or yield as measured full-campaign behavior.
- **Parquet entry:** measured cold evidence size or analytical query cost exceeds SQLite/Git expectations.
- **Semantic-index entry:** labeled recall shows deterministic L3 is insufficient at the measured catalog size.
- **Multi-worker entry:** measured single-writer backlog or latency prevents the campaign target and recovery semantics are specified.
- **Automatic Release entry:** at least three stable campaigns plus explicit controller and user approval.

## Reserved decisions

The controller still decides PR #7 merge, full campaign expansion, semantic quality thresholds, any new storage migration, multi-worker operation, high-risk publication, `v0.2.0`, and Release automation. A green test suite or campaign report is evidence for those decisions, not authorization to take them.
