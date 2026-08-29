# Plan adoption audit

**Status:** authoritative execution plan for the next bounded work package.  
**Baseline:** `main` at `6a54e7fc2748b02463fb269c7e9036f77812fae3` (merged PR #6).  
**Scope of this PR:** adopt the route and implement one replayable high-throughput vertical slice: SQLite runtime cutover, one official RSS connector, source-group/topic policy, five-queue ordering, L0–L3 deterministic evidence, checkpoint/no-op behavior, and a real canary. It does not merge or release.

## Binding 2026-08-29 scale revision

This section supersedes every conflicting ceiling, deferral, and “do not implement” statement elsewhere in this audit. It records the later explicit controller and user decision to move from a deliberately small calibration proposal to a high-throughput, quality-gated production route. Historical text remains below to show why the earlier boundary existed; it is not current execution authority.

### Adopted route

- The first complete campaign plans for **180–260 endpoints, 1,500–3,000 actual queries, 80,000–250,000 observations, 4,000–12,000 normalized candidates, and 400–1,000 deep reviews**. These are capacity and observation ranges, never minimums, maximum publication counts, or a reason to weaken evidence gates.
- Every qualified, original, independently useful Skill may be proposed in its review PR. The former 30–90 number is an estimate only: neither a cap nor a promise.
- Operation uses a dual-speed funnel: inexpensive acquisition/normalization runs broadly; semantic adjudication, synthesis, and evaluation consume the five priority queues continuously. `not_promoted` remains a retained decision with a reason and reactivation condition.
- A canary is the first 5–10% of the same campaign. It records technical, quality, and cost stop-loss metrics. When every applicable metric stays within policy, the runner continues to the remaining registered capacity without waiting after each small batch. A breach stops at a durable checkpoint and reports the smallest repair.
- The measured Git-JSON lifecycle bottleneck authorizes a **single-writer SQLite runtime store now**. Runtime source cursors, observations/discoveries, candidates, queue state, and decision records have one authority: SQLite. Published Skills, Plugin manifests, catalog, evals, release assets, and human-readable run/migration reports remain in Git.

### Migration authority and deletion condition

`docs/decisions/0002-adopt-sqlite-runtime-store.md` is the sole migration decision. The cutover is complete only when all of the following hold in one tested slice:

1. a temporary SQLite import validates source-state, discovery/candidate, and decision counts and stable ids against the legacy records;
2. the SQLite database is atomically installed and its schema/version validates;
3. `scan`, `status`, `review-queue`, and `apply` read/write only SQLite runtime data; a change to a legacy JSON file cannot affect them;
4. a repeated import is rejected or an explicit no-op, never a second writer; and
5. legacy runtime JSON (`state/harvest-state.json`, candidate lifecycle files, and decision-record files) is deleted from the active tree in the same cutover commit after the migration manifest records their counts and hashes.

There is no compatibility reader, dual write, fallback path, or feature flag after cutover. Git history preserves the deleted JSON snapshots; the migration manifest preserves auditable counts and ids. If validation fails, the temporary database is discarded and the old runtime remains authoritative until a repaired migration PR is reviewed.

### Current vertical slice and stop-loss

The immediately authorized slice is: existing high-trust document/Atom/JSON connectors -> explicit source group/topic metadata -> SQLite queue classes -> L0 source identity, L1 evidence identity, L2 capability fingerprint, L3 deterministic bounded recall -> transactional checkpoint/no-op -> one real canary.

The canary may only use T0/T1 official OpenAI format material, GitHub delivery material, and official Python packaging feeds/APIs. Registries remain discovery signals. Medical, legal, financial, real-world-control, and high-privilege candidates remain evidence-only and cannot be auto-published.

Stop the campaign and preserve its cursor/queue checkpoint on any failed atomic write, source failure rate above the policy after a meaningful sample, budget/Usage limit, malformed/untrusted input crossing a validated boundary, duplicate/idempotency invariant failure, evaluation/installation failure, or a runtime-store size/latency threshold. Missing Usage telemetry is written as `measured=false`; credits are never bought and auto top-up remains disabled. Luna may route/extract/triage, Terra handles ordinary comparison/implementation, and Sol is limited to difficult or high-impact review/final audit.

`v0.2.0` remains reserved but unreleased. This PR must not merge or create a Release; later release authority still requires a complete campaign, gates, and a fresh controller approval.

### Implemented slice and measured result

The binding route above is now exercised by this branch. `state/harvest.sqlite3` is the only runtime authority: the one-time importer recorded 13 source states, 110 discoveries, and 110 decisions before the legacy runtime JSON was deleted. `scan`, `status`, `review-queue`, `apply`, validation, and the harvest workflow use the SQLite store; published artifacts and readable reports remain Git files.

The first live run used the three policy groups. Its three-source structural canary passed, then automatically ramped to every currently unauthenticated executable policy endpoint (10 total). It made 10 successful requests, observed 110 feed/document items, enqueued 109 new normalized discovery candidates, and downloaded 289,733 bytes. Usage telemetry is `measured=false`; no deep semantic review or Skill publication was performed. The immediately preceding ramp attempt met an authenticated GitHub API `403`; it left a failed scan report, and the runner now records a campaign checkpoint rather than losing the successful canary state. `openai-plugin-catalog` remains registered but is deliberately outside the unauthenticated campaign selection until an official `gh` login is valid.

This is an operational vertical slice, **not** a claim that the 180–260 endpoint campaign is complete: three sources cannot simultaneously cover all three groups and be 5–10% of that future inventory. The automatic 3-to-10 ramp proves the current safe capacity. The next expansion gate is a versioned executable inventory large enough for a 5–10% same-campaign canary plus a query connector with durable topic cursors; neither is faked by relabeling this result.

## Purpose and authority

The attached “Codex Skill Harvester 全面规模化执行规划” was reread in full as an **untrusted planning input**. It is useful for options and risks, but it is not an implementation instruction, a source of operating facts, or a release commitment. Its suggested source text, URLs, package interfaces, cost figures, and directory tree do not gain authority by appearing in that input.

This audit resolves that input against the merged repository and the total-control decisions. Until a later, explicitly approved replacement, authority is singular at each boundary:

| Boundary | Sole authority now | Notes |
| --- | --- | --- |
| User and total-control decisions, release and merge permission | The delegated task instruction and its future explicit approvals | A PR or green CI never grants release or merge authority. |
| Current runtime behavior | `src/skill_harvester/` plus its tests | The active scan is `sources.load_registry` -> `run_scan`; review paging is `reporting.review_queue`; decisions are `decisions.recommend_decision` / `apply_decision`. |
| Existing source definitions and their actual trust values | `sources/registry.json` | Its current values remain `official`, `representative`, and `discovery`; T0–T4 is a future vocabulary, not a silent reinterpretation. |
| Current taxonomy and capability identity | `catalog/taxonomy.json` and `catalog/capabilities.json` | Taxonomy 1.0.0 already requires one canonical capability id, primary family, and facets. |
| Existing review-page and migration numeric policy | `config/scale-policy.json` | This is the only source for the current review default/maximum and storage migration triggers. |
| Executable campaign selection and stop-loss | `config/campaign-policy.json` | It is the sole runtime authority for the current three groups, canary, queue order, and stop-loss. This audit owns the long-range intent and entry conditions, not a duplicate machine policy. |
| Codex Skill and Plugin format | Official OpenAI documentation and official repositories only | Community material is discovery or comparison evidence, never format authority. |

`docs/architecture.md`, `docs/scale-audit.md`, and `docs/roadmap.md` remain explanatory records. They must not override the runtime files above. If a future change needs a new authority, it must retire or explicitly supersede the old one rather than create a fallback or dual-read path.

## Confirmed baseline, assumptions, and exclusions

### Confirmed

- PR #6 is merged. It established scale foundations: the three layers, taxonomy and canonical ids, reversible `not_promoted`, bounded policy-owned review pages, stage-owned metrics, a storage benchmark, and measured migration triggers.
- PR #6 is **not** a scalable production line. The current code has three adapters (`document`, `json-list`, and `atom`) in `sources.py`, source-level transactional selection, persisted source cursors, exact discovery-record dedupe, a seven-field exact fingerprint comparison, and file-based Git-JSON state.
- The active backend is `git-json-v1`. The validated migration triggers are 50,000 candidate records, 150,000 lifecycle files, 100,000 seen source items, a 32 MiB harvest state, or 60 seconds full validation. None is currently active.
- The published product is deliberately small: one published capability in one Plugin. That is evidence of one completed quality-gated slice, not a cap on the eventual catalog and not a claim that the world contains only one reusable workflow.
- The catalog taxonomy already has a primary family plus facets for domain, intent, inputs, outputs, tools, platforms, side effects, risk, volatility, maturity, and trust. It is versioned and extensible where declared.

### Working assumptions to test, not facts

- A bounded three-source-group campaign can show whether the existing Git-JSON path needs a small source/topic/queue extension before a storage decision is justified.
- Candidate retrieval can first be bounded deterministically with the existing fingerprint, taxonomy, aliases, and explicit fixture corpus; a semantic index is unnecessary until measured recall or comparison cost says otherwise.
- Usage credits may not be exposed through a reliable, attributable per-campaign meter. The initial budget contract must therefore work with `measured=false` and workload ceilings alone.

### Explicitly not doing in this work package

- No connector, source registry, source request, discovery query, raw-content download, or broad scan.
- No schema v3, storage interface, SQLite, Parquet, embedding, service queue, multi-worker, feature flag, compatibility shim, or dual-read path.
- No new Skill, Plugin, Collection, tag, Release, merge, or automatic semantic merge.
- No quality-rate claim for semantic recall, false merge, trigger recall, or costs without a labeled data set or authoritative measurement.

## Non-negotiable control decisions

1. **Foundation is not completion.** PR #6 is merged and is the correct base, but it is not evidence that the large-scale production system exists.
2. **Release policy.** `v0.2.0` is reserved as the next public version, not issued now. A human may release it only after: (a) the first vertical slice, (b) one real calibration campaign, (c) every applicable gate, and (d) a new total-control approval. Automatic Release is not considered until at least three stable campaigns, and still needs a separate approval.
3. **Model roles and spend stop.** Luna is only for high-throughput routing, extraction, and initial triage; Terra performs ordinary semantic comparison and implementation; Sol is reserved for difficult/high-impact decisions and final audit. If campaign-scoped Usage is reliably observable, its incremental ceiling is 100 credits. Credits must not be purchased and auto top-up must remain disabled. If Usage cannot be measured reliably, record `measured=false`; do not fabricate a price or substitute an estimate for measured cost.
4. **High-risk publication boundary.** Medical, legal, financial, real-world control, and high-privilege work may collect evidence in phase one, but automatic publication is blocked. Any publication in those areas needs explicit total-control and user approval. During the first three campaigns the system opens PRs only; total control decides every merge and release. Semantic merge remains supervised.

## Adoption ledger for the Pro plan

The status below applies to the plan's substantive sections, not merely its preferred filenames. “Deferred” means useful but blocked by evidence or by the first-slice boundary. “Rejected” means it must not be introduced on the proposed basis.

| Pro-plan area | Status | Decision, reason, and entry condition | Authority when it executes |
| --- | --- | --- | --- |
| Long-horizon capacity framing and three layers | **adopted** | Millions of observations and thousands of Skills are capacity envelopes, never publication quotas. Evidence/Discovery, Capability Registry, and Published Skills are already the architectural model. | `docs/architecture.md`; runtime records remain authoritative for their layer. |
| T0–T4 source tiers | **modified** | Adopt the vocabulary: T0 format authority, T1 official operational, T2 primary project, T3 representative, T4 discovery signal. Do not remap existing registry values or claim compatibility until one exercised registry migration has a validated contract. | Current `sources/registry.json` until a future, versioned registry schema is approved. |
| Connector expansion (HTTP/RSS/sitemap/GitHub/OpenAPI and registries) | **deferred** | The present three adapters remain in `sources.py`; no connector tree is pre-created. Add one connector only when a selected source group and fixtures require it, and prove changed/no-op/failure behavior. Package registries start as discovery signals, not operation authority. | Future connector slice specification and tested runtime code. |
| Domain × Intent coverage matrix | **modified** | Adopt the matrix as a planning lens, not a 90-day coverage or publication quota. Existing taxonomy facets remain the only validated classification schema. | `catalog/taxonomy.json`; future topic policy only after it is exercised. |
| Topic Bank and query generation | **adopted in principle; deferred in code** | Rotate explicit topics and retain cursors, but introduce only the smallest data contract used by the first three source groups. Do not create a `config/topics/` tree or thousands of generated queries in advance. | Future single campaign/topic policy file, once validated; this audit until then. |
| High-trust source groups and cadence | **adopted in principle** | The first calibration selects exactly three groups named below. “All high-trust sources” means all registered members of the selected group, checked incrementally; it never means re-downloading a whole site. | The future exercised source-group manifest and `sources/registry.json`. |
| Proposed `connectors/`, `extraction/`, `security/` module tree | **rejected now** | It is a speculative re-layout and would create empty abstractions or a parallel implementation before an actual boundary is proven. The first slice uses the minimum current call chain. | Existing `sources.py` remains sole runtime authority. |
| Five queues and weighted scheduling | **modified** | Adopt five logical queue classes: `urgent-impact`, `official-gap`, `reactivation`, `novel-discovery`, and `aged-backlog`. The first slice implements deterministic classification and bounded ordering only—no service scheduler, quota optimization, or starvation SLO. | Future tested queue fields/order in the current reporting path; `config/scale-policy.json` still owns page size. |
| L0–L4 deduplication | **adopted with staged evidence** | L0 source identity, L1 exact evidence, L2 structural fingerprint, L3 bounded deterministic recall, L4 supervised semantic judgement are the target. The current code already has portions of L0/L1 and exact seven-field L2. First slice proves L0–L3 with fixtures; L4 is budgeted human/Codex review, never an automatic merge. | Current decision code until a tested replacement; any derived index is non-authoritative. |
| Numeric dedupe/quality thresholds from the Pro plan | **deferred** | No `>=98%` recall, false-merge rate, or similar value is a gate until a labeled, adjudicated set measures it. | Future labeled-set protocol and explicit total-control threshold approval. |
| Candidate/artifact/capability lifecycle and reactivation | **adopted in principle; deferred schema change** | Keep three distinct lifecycles, durable decisions, aliases/variants, and reversible `not_promoted`. Current schema v2 and its required reactivation conditions remain active. Schema v3 is not started until a single migration slice is approved by evidence. | Current catalog/decision schemas; `docs/schema-migrations.md` for existing migration practice. |
| Evidence Pack through synthesis, evaluations, install, and originality | **adopted** | Promotion continues to require provenance, original synthesis, format/trigger/E2E/installation checks, and no unlicensed copying. The proposed count of examples is a future evaluation design input, not a retroactive gate claim. | Existing validators/evals and official OpenAI format sources; future gate contract only when tested. |
| Plugin/Collection organization by install intent | **adopted** | Small coherent task-domain Plugin boundaries are retained. Collection files and install previews are deferred until multiple real Plugins require them; no source-site taxonomy is used for product packaging. | Existing Plugin manifest and published capability catalog. |
| Reverse evidence impact / revalidation graph | **deferred** | Useful once there are enough published capabilities and evidence links to query. Implement after the first calibration records show update/revalidation demand. | Future approved evidence-link slice. |
| Git-JSON -> SQLite -> Parquet -> rebuildable semantic index | **adopted as a measured route** | Migration only opens after the existing machine policy trigger and benchmark evidence. SQLite is the likely hot-state option, Parquet is cold metadata only, and semantic retrieval is derived recall. No storage interface, shadow run, dual-read, shim, flag, database, or embedding is created now. | `config/scale-policy.json` and the existing storage ADR; a later migration ADR supplies the sole implementation decision. |
| Shards, idempotency, checkpoints, retries, no-op | **modified** | Preserve source-level transactional selection and no-op behavior now. The first slice adds only the replay data it actually needs; staged multi-dimensional shard keys and retry taxonomy wait for a connector that needs them. Reaching a budget preserves its cursor and queue state, never creates `not_promoted`. | Existing `run_scan` state semantics, then one tested slice contract. |
| Security, license, injection, and supply-chain hardening | **adopted with current boundary** | External material stays untrusted data; raw bodies remain temporary; downloaded scripts are never run; unknown/restricted licensing blocks copying. Add new checks only alongside the boundary that introduces the risk. | Repository `AGENTS.md`, source/decision validation, and official source policy. |
| Round metrics and SLOs | **modified** | Keep stage-owned metrics and write `measured=false` for unexecuted/unobservable stages. The Pro plan's dashboards and rates are not commitments; metrics need no invented zeros, cost, or quality results. | Current reports for current stages; later canonical run-report schema after it is exercised. |
| 30/60/90-day counts, large campaign estimates, and cost projections | **rejected as operating targets** | They conflict with quality-first bounded operation and imply unsupported capacity/cost facts. They may be retained only as non-binding historical ideas in the untrusted input, not copied into roadmap or policy. | This audit and future measured campaign reports. |
| Work-package order (schema v3 first, then storage interface, connector split, etc.) | **rejected** | It front-loads abstractions without evidence and conflicts with the controller-selected first vertical slice. Replace it with the 0–30 day mainline below. | This audit. |
| Luna/Terra/Sol division, supervised PR workflow, and high-risk block | **adopted** | These are controller decisions, not optional suggestions. They apply before the first campaign and survive any implementation refactor. | This audit until superseded by a controller-approved policy. |

## 0–30 day mainline

The sole objective is to prove one bounded, replayable calibration path—not to maximize coverage, count candidates, or issue `v0.2.0`.

1. **This audit (complete in this PR).** Freeze the adopted route, authority map, hard ceilings, and first-slice acceptance criteria.
2. **First vertical-slice implementation (a future, separately authorized PR).** Extend only the existing scan/review/decision path to express one source group, one selected topic, five logical queues, and L0–L3 replay data. It must use fixtures before any public request.
3. **Labeled-set preparation (in that same future slice or an immediately preceding approved measurement PR).** Establish the adjudicated examples and reporting method below. Do not announce recall or false-merge quality before it exists.
4. **One real calibration campaign (a future, separately authorized run).** Use the exact hard ceilings below, retain every unprocessed cursor/queue item, open a PR only for reviewed changes, and stop at the first ceiling.
5. **Checkpoint.** Report measured results, gaps, and whether a second campaign or a narrow corrective slice is justified. Only total control can authorize the next campaign, merge, or any `v0.2.0` release evaluation.

No parallel connector program, package registry expansion, broad query sweep, lifecycle migration, or storage migration belongs on this mainline.

## First calibration campaign contract

### Selected high-trust source groups

The future manifest may name only these groups during campaign one:

| Group | Role | Trust interpretation |
| --- | --- | --- |
| OpenAI format authority | Skill/Plugin format, installation, and evaluation constraints | T0 |
| GitHub delivery | Repository, PR, CI, Release, and delivery workflows | T1/T2 evidence as the actual registered source establishes |
| Python packaging | Packaging and publishing workflows | T1/T2 evidence as the actual registered source establishes |

The names identify scope, not permission to fetch every related endpoint now. New endpoints require the future slice's validated manifest and must remain within the ceiling.

### Hard stop ceilings

Every campaign must emit its measured values and stop at the first reached ceiling. The number six is a **synthesis-proposal maximum**, never a publication target; there is no minimum published-Skill count.

| Limit | Ceiling | Checkpoint behavior |
| --- | ---: | --- |
| High-trust source groups | 3 | Do not add a fourth group. |
| Endpoints | 24 | Preserve remaining discovery cursor. |
| Actual discovery queries | 60 | Do not mark unrun queries as non-promotion. |
| Source requests | 250 | Stop safely and retain source cursor. |
| Downloaded bytes | 100 MB | Stop before exceeding; record bytes actually measured. |
| Observations | 2,000 | Preserve remaining page/topic cursor. |
| Normalized candidates | 300 | Leave excess candidates queued. |
| L4 semantic reviews | 60 | Leave candidates in the review queue. |
| Synthesis proposals | 6 | Do not convert the remaining candidates to `not_promoted`. |
| E2E time | 180 minutes | Preserve proposal/evaluation state. |
| Semantic-review tokens | 3,000,000 | Stop semantic work and preserve queue state. |
| Incremental Usage credits | 100 only if reliably observable | If not reliably observable, set `measured=false`; the workload limits still stop the campaign. |

“Reliably observable” means a campaign-attributable Usage reading can be captured before and after the campaign without guessing, purchasing credits, or enabling auto top-up. A missing or ambiguous meter is not an error to compensate for with an estimated currency value.

## First vertical-slice implementation boundary

The next implementation must be a thin replayable extension of current behavior, not a new subsystem.

### Existing call path to retain

```text
sources/registry.json
  -> sources.load_registry()
  -> sources.run_scan() (source-level atomic state and candidate inbox)
  -> reporting.review_queue() (policy-bounded page)
  -> decisions.recommend_decision() / apply_decision()
```

### Minimum additions allowed later

1. **One exercised source-group and topic contract.** It may select the three named groups and at most the campaign limits. It must refer to actual registered sources; it must not contain a future connector catalog, fake endpoint inventory, or generated query bank.
2. **Five logical queue labels in the existing review path.** Classification must be deterministic from persisted facts. The first slice needs clear precedence and fixtures for `urgent-impact`, `official-gap`, `reactivation`, `novel-discovery`, and `aged-backlog`; it does not need a worker, lease, service, or percentage allocator.
3. **Replayable L0–L3 evidence.** Persist only the keys required to demonstrate: L0 source item/revision idempotency; L1 normalized evidence identity; L2 normalized seven-field fingerprint; L3 bounded deterministic comparison candidates. A derived recall list may never decide merge/create.
4. **Budget checkpoint report.** Record only stages run, their actual counters, `measured=false` where relevant, next cursors, pending queue items, and why execution stopped. A limit stop is not a negative decision.
5. **Fixtures before network.** Cover exact duplicate, source revision change, structurally distinct candidate, bounded L3 recall, all five queue placements, continuation, and no-op replay. Do not execute third-party scripts.

### Required acceptance evidence

- A controlled fixture run can be executed twice, with the second pass proving no-op/idempotent behavior.
- A bounded L3 recall list is deterministic and does not alter L4's supervised decision authority.
- Every ceiling produces a checkpoint with a continuation cursor or pending item, not a `not_promoted` record.
- Existing `config/scale-policy.json` still solely controls review default and maximum; any campaign file has one separate, explicitly scoped authority with no duplicate values elsewhere.
- Repository validator, full tests, and the relevant new fixtures pass on Ubuntu and Windows CI before any real campaign.

## Labeled-set measurement before quality claims

The first slice must create a small, versioned, adjudicated fixture corpus before it reports recall, false merge, or semantic automation quality.

| Item | Required method |
| --- | --- |
| Unit under review | A candidate-to-capability pair plus its bounded L3 candidate list and cited evidence facts. |
| Labels | `exact_duplicate`, `semantic_equivalent`, `update`, `variant`, `distinct`, or `uncertain`; `uncertain` is retained and excluded from favorable claims. |
| Ground truth | At least two recorded human/total-control adjudications for disputed examples, with rationale and evidence references. A model-only label is not ground truth. |
| Splits | Keep a fixed regression set separate from any later tuning/examples used to change retrieval. |
| Measurements | Report candidate-recall coverage of known matching targets, false-merge rate only among adjudicated merge decisions, and the count/exclusion of uncertain examples. |
| Reporting | Include sample size, label version, inclusion/exclusion rules, and confidence limitations. Never report an unlabeled rate as zero. |

No threshold becomes a release or automation gate merely because it appears in the Pro plan. A future threshold needs this corpus, measured results, and total-control approval.

## Later milestones and entry conditions

| Milestone | Earliest entry condition | Still blocked until |
| --- | --- | --- |
| Additional connector | The first slice shows an actual source group cannot be represented by the tested current adapters. | A connector-specific fixture contract, bounded request behavior, and explicit approval. |
| Schema v3/lifecycle expansion | A recorded first-slice field cannot be represented by current schemas without ambiguity. | One migration plan, fixtures, and a decision about the sole authoritative schema. |
| SQLite | A named `config/scale-policy.json` trigger is crossed and a benchmark identifies the bottleneck. | A migration ADR and one migration slice; no shadow/dual-read before that decision. |
| Parquet | Cold evidence volume or analytics needs exceed the selected SQLite/Git envelope. | A measured storage decision; it cannot own hot capability state. |
| Semantic index | Labeled set shows deterministic L3 recall/cost is insufficient at a measured catalog size. | A rebuild proof and supervised L4 decisions. |
| Reverse evidence impact | Calibration demonstrates evidence changes affecting multiple published capabilities. | A tested lineage slice and policy for revalidation. |
| Multi-worker/service queue | Real throughput requires it and concurrent-writer evidence exists. | Ownership/lease/recovery evidence and explicit approval. |
| Automatic Release | At least three stable campaigns and explicit later decision. | All release gates and user/total-control approval. |

## Decisions still reserved for total control

- Authorize the first implementation slice after reviewing this PR.
- Authorize the real calibration campaign, its final registered endpoints, and whether Usage can be observed reliably.
- Decide campaign continuation after its checkpoint; a green implementation PR does not authorize a network run.
- Approve every merge/release during the first three campaigns and any high-risk-domain publication thereafter.
- Approve any semantic quality threshold, storage migration, third-party runtime dependency, service queue, public Collection/product-line change, or automatic Release policy.

## Execution checklist for the next worker

1. Start from the then-current clean `main` on a new `codex/` branch; do not touch the outer workspace or unrelated repositories.
2. Read this audit, the current source/decision/reporting path, `config/scale-policy.json`, and the existing migration ADR before editing.
3. Implement only the five allowed additions above with failing fixtures first. Do not scaffold inactive module trees.
4. Run repository validation, the full suite, and the new focused tests locally; push an exact-path PR and wait for both CI platforms.
5. Stop. Do not scan, merge, tag, release, or create a new public Skill without a new total-control instruction.
