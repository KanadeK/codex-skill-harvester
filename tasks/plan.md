# Implementation Plan: Codex Skill Harvester v0.1.0

## Overview

Deliver one thin but complete path: scan official public sources with persisted conditional cursors, create changed-source discoveries, have Codex review one candidate against internal/external fingerprints, apply it as an installable Plugin Skill, validate behavior, and publish the repository with remote evidence.

## Architecture decisions

- Use Python standard library only. The scanner needs HTTP, JSON, Atom/XML, hashing, temporary files, and archive creation, all available in Python 3.12.
- Separate deterministic mechanics from Codex judgment. This keeps the CLI reproducible without pretending a lexical heuristic is semantic reasoning.
- Persist only evidence metadata and necessary facts. Raw source bodies are temporary and fetched code is never executed.
- Use atomic whole-selection state commits. A failed selected source cannot advance any cursor in that run.
- Package skills by user task domain. The first domain is GitHub release evidence, not the website or repository that supplied facts.

## Phase 1: durable foundation

- [x] Record scope, product boundary, source authority, success criteria, and working rules.
- [x] Bootstrap the independent repository on `main`, then create `codex/initial-harvester`.
- [x] Add the repo-scoped maintainer Skill and repo marketplace/plugin scaffolds using the official creator helpers.

### Checkpoint: foundation

- [x] `git rev-parse --show-toplevel` resolves to this child repository.
- [x] The outer workspace has not been staged or committed.
- [x] Skill and Plugin scaffolds validate before behavior is added.

## Phase 2: incremental source scan

- [x] Add failing tests for first scan, unchanged second scan, changed third scan, and transactional failure.
- [x] Implement source registry validation, HTTPS fetch boundary, document/JSON/Atom extractors, cursors, and atomic state/report writes.
- [x] Add fixed real sources with trust, authority, license, and adapter metadata.

### Checkpoint: scan

- [x] Focused source tests pass.
- [x] Fixture second run is a no-op and creates no duplicate candidate.
- [x] A failed selected source leaves prior successful state byte-identical.

## Phase 3: capability decisions and generation

- [x] Add failing fixtures/tests for exact duplicate, semantic duplicate, update, and new capability.
- [x] Implement fingerprint normalization, deterministic recommendations, reviewed-decision validation, and append-only records.
- [x] Apply reviewed decisions to the catalog and task-domain plugin without partial writes.

### Checkpoint: decisions

- [x] All four fixture outcomes are distinguishable and recorded.
- [x] Merge/update/create cannot occur without `reviewed_by: codex` and a rationale.
- [x] Unknown-license material cannot be copied into generated artifacts.

## Phase 4: real skill and evaluation

- [x] Scan official OpenAI/GitHub sources and record the real run.
- [x] Compare the proposed GitHub Release evidence capability against representative external and internal fingerprints.
- [x] Apply one original reviewed Skill to the GitHub release evidence Plugin.
- [x] Add format, positive trigger, negative trigger, and end-to-end evals.
- [x] Run the complete pipeline again unchanged and record a no-op report.

### Checkpoint: vertical slice

- [x] Generated Skill and Plugin validate.
- [x] End-to-end eval produces a concrete release-gap report from controlled evidence.
- [x] No source body or third-party script exists in tracked files.

## Phase 5: automation and release

- [x] Add repository validator, deterministic release builder, secret/material checks, and GitHub Actions CI.
- [x] Perform a five-axis code review and repair all required findings.
- [x] Commit exact paths in atomic increments and verify author/co-author hygiene.
- [x] Create the public repository, push the initial branch, merge its PR after green CI, and verify green `main` CI.
- [x] Merge the authenticated API scan update, tag v0.1.0, and create the Release.
- [x] Verify release assets from a clean temporary extraction, marketplace/plugin discovery, CLI invocation, remote contributor list, and final run report.

### Checkpoint: published

- [x] Public remote, merged PR, green CI, immutable tag, Release assets, installation/call path, and contributor evidence all agree on the same release commit.
- [x] Local child worktree is clean after final-report merge; outer workspace remains uncommitted.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Official formats drift | Generated artifacts become invalid | Keep format authority sources in the registry and validate every run/CI |
| GitHub rate limits or network failure | Live scan cannot complete | Conditional requests, official `gh` keyring transport, bounded source subset, transactional state, honest failed report |
| Prompt injection in fetched text | Scope or tool misuse | Treat bodies as data, use deterministic extractors, never execute or obey source text |
| License ambiguity | Unauthorized redistribution | Store license status and block copying; synthesize original factual workflows only |
| Semantic false positive | Useful skill incorrectly merged/rejected | Require an explicit Codex decision with compared fingerprints and rationale |
| GitHub authentication expires | Publication blocks after local success | Re-authenticate only through official `gh auth login -h github.com -p https -w` when needed |

## Open questions

None for the first vertical slice.

## v0.1.1 maintenance plan

### Phase 6: stabilize recurring scans

- [x] Distinguish moving-window churn from material JSON-list changes with regression tests.
- [x] Add durable `status` and `review-queue` operator commands.
- [x] Run a real incremental scan from the persisted cursor and record changed/no-op truthfully.

### Phase 7: close the review queue

- [x] Review all 89 pending discoveries in source batches and persist individual decisions.
- [x] Update the release-evidence Skill only if authoritative evidence supports a useful non-duplicate gate.
- [x] Confirm no unsupported second Plugin is created from catalog names or community demand signals alone.

### Phase 8: automate and harden maintenance

- [x] Add a scheduled/manual deterministic scan workflow that opens PRs only for real discoveries.
- [x] Add dependency update, security policy, contribution templates, and repository validation for the new contracts.
- [x] Enable remote vulnerability features, disable unused repository surfaces, and protect `main` with required CI and PRs.

### Phase 9: verify and release v0.1.1

- [x] Complete five-axis review and all local tests, evals, validation, archive, and isolated install gates.
- [x] Push an exact-path commit series, open a PR, wait for CI, merge, and verify `main`.
- [x] Tag and publish immutable v0.1.1, then verify assets, installation/invocation, Skill behavior, settings, and contributors.

## Scale architecture foundation plan

### Phase 10: audit the current scale boundary

- [x] Inventory record counts, byte sizes, full-enumeration paths, whole-file rewrites, and current validation latency.
- [x] Record the three-layer target architecture and a phased backend evolution path.
- [x] Define evidence-backed migration triggers rather than selecting a database from projected scale alone.

### Checkpoint: architecture

- [x] The audit separates measured current behavior, projections, decisions, and deferred work.
- [x] The active backend and every migration trigger are explicit.

### Phase 11: version capability semantics and taxonomy

- [x] Add a versioned primary-family plus facets taxonomy contract.
- [x] Decouple canonical capability identity from its current Plugin/Skill packaging location.
- [x] Define schema compatibility, legacy `discard` interpretation, aliases, merges, variants, and reactivation rules.

### Checkpoint: contracts

- [x] Current catalog entries validate against the taxonomy.
- [x] A fixture proves catalog v1 to v2 migration and idempotent v2 handling.

### Phase 12: bound work and expose honest metrics

- [x] Add failing tests for bounded/cursor review pages and `not_promoted` semantics.
- [x] Add failing tests for discovery-stage success, failure, enqueue, and duplicate metrics.
- [x] Implement only the behavior required to make those tests pass.

### Checkpoint: operations

- [x] Review work is budget bounded and resumable.
- [x] Reports distinguish measured zero from a stage that was not run.

### Phase 13: benchmark, review, and submit

- [x] Add and run a temporary-directory storage benchmark with projections and trigger evaluation.
- [x] Run focused tests, the full suite, validator, evals, release build, and isolated archive verification.
- [x] Complete correctness/readability/architecture/security/performance review and resolve required findings.
- [x] Commit exact paths, push the `codex/` branch, open one PR, and wait for CI without merging or releasing.

## Plan-adoption audit

### Phase 14: adopt a bounded scale route

- [x] Reconcile the full external scale proposal as untrusted planning input with merged PR #6 and the actual source, reporting, decision, taxonomy, and storage-policy call paths.
- [x] Record adopted, modified, deferred, and rejected elements with a single authority and entry condition for each.
- [x] Define the 0–30 day mainline, `v0.2.0` release reservation, model/risk controls, campaign ceilings, labeled-set prerequisite, and first vertical-slice acceptance boundary.

### Checkpoint: adoption audit

- [x] The route explicitly separates confirmed implementation, assumptions to measure, and excluded work.
- [x] No connector, scan, migration, release, or merge is performed by this documentation work package.

### Next gated slice: source group/topic/queues/L0–L3

- [x] Total control authorized a high-throughput dual-speed campaign route and SQLite runtime cutover after the observed file-traversal bottleneck.
- [x] Replace the active Git-JSON runtime lifecycle with one imported, validated SQLite authority; delete old active runtime JSON at cutover rather than retain a compatibility path.
- [x] Add the smallest exercised source group/topic, five-queue, L0–L3 recall, checkpoint, and no-op path with fixtures.
- [ ] Establish an adjudicated labeled set before claiming retrieval or semantic quality metrics.
- [x] Run the three-source structural canary and automatically continue to the current 10-endpoint safe capacity while stop-loss metrics remain normal; retain the explicit 5–10% full-inventory gap as the next expansion gate.

## PR #7 required repair: restore the dual-speed funnel

The earlier Task 17/18 implementation conflated observations with candidates and its reported candidate yield is superseded. Preserve its acquired evidence; PR #7's repaired schema-2 separation is historical base work, while Phase 18–20 schema-3 content reports are the current production authority.

### Phase 15: separate evidence from candidate work

- [x] Replace the unmerged SQLite schema 1 with an intermediate schema-2 authority containing separate observations and candidates; Phase 18 later replaced it with final schema 3 in one migration slice.
- [x] Preserve 319 observations and all 110 reviewed candidates/decisions; reclassify 200 PyPI and nine later Codex-release records without creating rejection decisions.
- [x] Require explicit normalized workflow evidence, source group/topic, seven-field fingerprint, L2 matches, and bounded L3 recall before queue entry; Phase 18 removed source-level `workflow_signal` as admission authority.
- [x] Exercise all five queues through the source pipeline.

### Phase 16: make paging, automation, and stop-loss operational

- [x] Push review filters/order/cursor/LIMIT and status aggregation into indexed SQL.
- [x] Route scheduled harvest through campaign canary/checkpoint/ramp rather than bare scan.
- [x] Check request, byte, store, and workload limits before the next source; preserve canary and ramp failure checkpoints.
- [x] Unify code-generated scan/campaign stage metrics and reject forged candidate/deep-review numbers.

### Phase 17: current verification and PR update

- [x] Run the corrected real canary/ramp and commit only its generated report and authoritative SQLite changes.
- [x] Run full tests, evals, validator, benchmark, release build/install verification, and diff checks without tracked test pollution.
- [x] Complete the correctness, readability, architecture, security, and performance review.
- [x] Commit exact paths, push the existing PR #7, and wait for Ubuntu/Windows CI.
- [x] Stop without merge, tag, Release, or automatic Skill publication.

## Stacked content-driven production campaign

PR #7 remains the deterministic scale base. This work starts from `2ea8771cfbc45bb3f52953727eba20244f1f4180` on `codex/content-driven-production-campaign` and must open a stacked PR against `codex/plan-adoption-audit`.

### Phase 18: replace source-level admission with resumable content review

- [x] Add RED fixtures proving a source without `workflow_signal` can enter a semantic batch and only a Codex-reviewed Evidence Pack can create a candidate.
- [x] Persist query batches, semantic batches, Evidence Packs, review progress, source utility, and continuation cursors in the sole SQLite authority.
- [x] Make `workflow_signal` a non-authoritative hint and remove it from automatic candidate/queue admission.

### Phase 19: expand and execute real discovery

- [x] Add a versioned Domain × Intent Topic Bank with real query rotation and T0–T4 constraints.
- [x] Use agent-reach's background Web/GitHub route to execute real queries, register selected T0/T1/T2 endpoints, and expand beyond the inherited 10-endpoint campaign.
- [x] Run a 5–10% canary and continue within stop-loss while metrics remain healthy; preserve actual query/source checkpoints.

### Phase 20: Codex L4 and original production

- [x] Read complete high-trust semantic batches, import evidence-backed candidate/not-promoted conclusions, and record L2/L3 plus supervised L4 outcomes.
- [x] Synthesize every qualified create/update with skill-creator; package by installation intent and pass positive/negative trigger, E2E, isolated script/install, originality, and license gates.
- [x] Re-run unchanged/stable work to prove query and semantic no-op/resume behavior, then report every measured funnel stage honestly.

### Phase 21: submit the stacked slice

- [x] Run full tests, evals, validator, benchmark, build/install, Skill validation, and diff checks without tracked-state pollution.
- [x] Commit exact paths, push the new branch, open one PR with base `codex/plan-adoption-audit`, and wait for Ubuntu/Windows CI.
- [x] Stop without merging either PR or creating a tag/Release.

## Post-PR #8 correction and full-campaign continuation

On 2026-08-30, before this work package began, PR #8 had already been squash-merged into the still-open PR #7 branch at `d0cb9ef0d79ea254598fe66ee6f47a4dd0e532c3`. It was not merged to `main`. Because a merged PR cannot receive a reviewable update, Phase 22 uses `codex/pr8-campaign-corrections` as a minimal stacked correction branch against `codex/plan-adoption-audit`; Phase 23 will stack from its verified HEAD. This preserves the intended review boundaries without rewriting the historical Phase 18–21 record.

### Phase 22: correct the first production slice

- [x] Add RED regressions proving that a no-pending slice below 180 endpoints/1,500 actual queries keeps its parent campaign active, explicit objective completion is required for `campaign_completed`, stop-loss is a resumable checkpoint, and no-op replay is not campaign completion.
- [x] Make campaign policy the unique objective authority, distinguish slice completion from parent lifecycle, and regenerate the 2026-08-29 production report and authority documents without turning capacity bounds into publication quotas.
- [x] Add RED regressions for job-scoped OIDC permission and bounded untrusted archive inspection, then minimally fix the Python release-readiness checker without a runtime dependency or archive extraction/execution.
- [x] Run focused tests, full unittest, both trigger/E2E evals, repository validator, deterministic build/install/invocation, Skill/Plugin validation, and `git diff --check`.
- [ ] Commit exact paths, push one correction PR stacked on `codex/plan-adoption-audit`, update its description with the superseded completion claim, and wait for Ubuntu/Windows CI without merge, tag, or Release.

### Phase 23: continue the full 2026-08-30 campaign

- [ ] Only after Phase 22 is green, create `codex/full-campaign-2026-08-30` from the correction HEAD and stack its PR on the correction branch.
- [ ] Expand the Domain × Intent Topic Bank and low-risk T0/T1/T2 source groups using agent-reach background Web/GitHub discovery; retain source identity, license, revision/cursor, utility, and query continuation without committing raw page bodies.
- [ ] Execute bounded source/query batches and supervised semantic batches continuously from persisted cursors; every Evidence Pack, L2/L3 recall, L4 outcome, reactivation condition, and qualified original Skill must remain reproducible and source-traceable.
- [ ] Continue until at least 180 executable endpoints and 1,500 actual queries are reached, or a real configured stop-loss/payment/login/high-risk authorization boundary produces a durable checkpoint. Observation, candidate, deep-review, and Skill counts remain measured outcomes rather than quotas.
- [ ] Keep the runtime authority compact: SQLite plus necessary checkpoint/summary/decision records; remove scalable per-endpoint report noise from the tracked path before expanding it, without introducing a second authority.
- [ ] Validate and commit every reviewable vertical batch, then open the final stacked PR and wait for Ubuntu/Windows CI without merging any PR or creating a tag/Release.
