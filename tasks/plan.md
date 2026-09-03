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

The earlier Task 17/18 implementation conflated observations with candidates and its reported candidate yield is superseded. Preserve its acquired evidence; PR #7's repaired schema-2 separation and Phase 18–20 schema-3 reports are historical inputs, while the schema-4 SQLite store is the current runtime authority.

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
- [x] Commit exact paths, push one correction PR stacked on `codex/plan-adoption-audit`, update its description with the superseded completion claim, and wait for Ubuntu/Windows CI without merge, tag, or Release.

### Phase 23: continue the full 2026-08-30 campaign

- [x] After Phase 22 passed locally and in Ubuntu/Windows CI, create `codex/full-campaign-2026-08-30` from correction HEAD `7aa8f86`; opening its stacked PR remains a later submission step.
- [x] Use agent-reach background Web discovery and official GitHub metadata to expand the Domain × Intent Topic Bank to 1,622 unique queries and the inventory to 204 revision-pinned executable endpoints, including comparison-only T3 Skills used only for semantic deduplication. No raw page bodies are committed.
- [x] Execute bounded source/query batches and supervised semantic batches continuously from persisted cursors; every Evidence Pack, L2/L3 recall, L4 outcome, reactivation condition, and qualified original Skill remains reproducible and source-traceable.
- [x] Reach 204 executable endpoints and 1,622 actual queries without a stop-loss. Observation, candidate, deep-review, and Skill counts remain measured outcomes rather than quotas.
- [x] Keep the runtime authority compact: SQLite plus necessary checkpoint/summary/decision records. Campaign scans now embed bounded run summaries in the parent report without creating per-endpoint tracked reports; standalone `scan` retains its explicit report behavior and no second authority was added.
- [x] Validate and commit every reviewable vertical batch, then open stacked PR #10 against `codex/pr8-campaign-corrections`; implementation HEAD `59b0734` is `CLEAN` with passing Ubuntu/Windows CI, and no PR, tag, or Release was merged or created.

Completion checkpoint on 2026-08-30: the sole SQLite authority contains 204 registered and scanned endpoints, 1,204 observations, 168 Evidence Packs, 136 applied L4 decisions, and eight Skills. The query cycle completed all 1,622 queries in 1,626 attempts, retaining four recoverable GitHub rate-limit failures and 151 discovery hits. Across the eight campaign semantic batches, 217 observations produced 58 Evidence Packs, 26 candidates, 263 L3 recalls, and 26 L4 outcomes: seven creates, three updates, one merge, and 15 `not_promoted`. The final 204-endpoint ramp completed with 204 successes, 517,498 downloaded bytes, 116 inserted observations, and no source failure. Query, semantic, and stable-source replay are no-op; the capacity objective is met. The 128-test suite, eight Skill evals, validator, benchmark, deterministic build/install/invocation, and diff checks pass locally. PR #10 is open and `CLEAN`; implementation HEAD `59b0734` passed Ubuntu/Windows CI. The final documentation-only HEAD is rechecked by CI before handoff.

## Daily Life Skills pilot

Remote baseline verified on 2026-08-30: `main` remains `6a54e7f`; PR #7 and PR #9 are open; PR #8 is merged only into the PR #7 branch; PR #10 is merged only into the PR #9 branch; and `origin/codex/pr8-campaign-corrections` is `034a1f0`. This work runs on `codex/daily-life-skills-pilot-2026-08-30` and will stack on that correction branch without merging or releasing.

### Phase 24: make Daily Life and discovery-hit review first-class

- [x] Register `daily-life` as the user-facing top-level domain with the first families `fresh-market-and-grocery-shopping`, `laundry-and-clothing-care`, and `home-cooking-and-meal-preparation`.
- [x] Clarify the existing seven-field fingerprint so `platforms` means software platform or real execution environment; add only the taxonomy values needed by exercised life capabilities, with no fingerprint schema fork or dual meaning.
- [x] Add RED tests for a single SQLite discovery-hit lifecycle: `pending -> selected_endpoint|duplicate|not_selected`, bounded partial review/resume, duplicate hits, invalid license/source metadata, selection failure/reopen, web hits, and no-op.
- [x] Persist query-to-hit provenance and reviewed metadata in the sole runtime authority; selected endpoints pass URL, identity, revision/cursor, license, duplicate, registry, and reproducible-scan validation before remaining selected.
- [x] Make query and production reports distinguish raw hits, pending review, selected, duplicate, not selected, and conversion rate. Completed query execution no longer implies completed hit review.

Checkpoint: the existing query executor may continue producing untrusted hit metadata, but only a Codex-reviewed discovery decision may register a source. No JSON inbox becomes a second authority.

### Phase 25: build the bilingual Scenario Bank and evidence base

- [x] Use agent-reach background search/web routes to select Chinese and English T0/T1/T2 sources across consumer/food safety, textile care, appliance/garment instructions, and cooking education; retain community material only as discovery signal.
- [x] Define 63 specific scenarios, 21 in each Daily Life family. Every scenario records locality/equipment assumptions, safety boundary, source refs, and a final `create|merge|not_promoted` outcome.
- [x] Scan 13 selected sources from persisted cursors, review 13 observations into 12 Evidence Packs, and carry nine independent capabilities through 156 L3 recalls and supervised L4. Three unsafe evidence packs and nine high-risk/unsupported scenarios remain not promoted.
- [x] Keep raw pages temporary and commit only compact provenance, the Scenario Bank, SQLite state, decisions, and campaign reports.

Checkpoint: 60+ scenarios have no pending outcome; counts are review coverage, never a Skill quota.

### Phase 26: synthesize human-executed instruction-only Skills

- [x] Create nine qualified original capabilities under exactly three installation-intent Plugins. Broad concepts remain families; nearby scenarios merge into the same canonical capability.
- [x] Keep all nine Skills instruction-only; no script was invented for appearance, and physical action remains the user's responsibility.
- [x] Make Chinese trigger and anti-trigger cases first-class, preserve English discovery, ask only missing critical conditions, and support plan / one-step-at-a-time / recovery modes without claiming physical completion.
- [x] Extend evals minimally for instruction-only workflows: nine files cover 36 trigger decisions and 27 realistic plan/live/recovery responses with 243 behavioral gates.

Checkpoint: every generated Skill passes source, originality, non-overlap, trigger, instruction-only E2E, safety, Plugin format, and isolated installation/invocation review.

### Phase 27: execute, validate, and submit the life campaign

- [x] Run reviewable vertical batches until all 63 scenarios are resolved and every family has three installable Skills; this is a complete pilot rather than three demonstrations.
- [x] Prove discovery review, query rotation, semantic processing, and a stable Chinese source replay resume or no-op from SQLite; Usage remains `measured=false` without an authoritative meter.
- [x] Run 146 unittest cases, 17 evals, repository validator, SQLite-v4 benchmark, deterministic build of 11 Plugins, isolated install/invocation, independent five-axis Skill review, and diff checks. Official standalone Skill/Plugin validators were attempted but unavailable because their local environment lacks PyYAML; the repository validator covers the committed format.
- [x] Commit exact paths, push `codex/daily-life-skills-pilot-2026-08-30`, open stacked PR #11 against `codex/pr8-campaign-corrections`, and verify implementation HEAD `e290fdf` is `CLEAN` with passing Ubuntu/Windows CI; no PR, tag, or Release was merged or created.

Local content checkpoint: 20 scoped queries completed without query failure and produced 18 unique hits. Thirteen remained selected after reproducible scans; five authoritative pages that returned HTTP 403 were reopened and retained as `not_selected`. The 13 scanned sources span Hong Kong (5), United States (6), Canada (1), and a global textile authority (1), with four Chinese and nine English endpoints. Thirteen observations produced 12 Evidence Packs, nine candidates, 156 L3 recalls, three evidence-level safety non-promotions, and nine L4 creates. The Scenario Bank holds 63 final outcomes (9 create, 45 merge, 9 not promoted), and all query/semantic/stable-source replay is no-op with zero pending.

Local verification checkpoint: 146 tests, 17 eval files, the code-rebuildable Daily Life report, repository validator, SQLite benchmark, deterministic source/11-Plugin build, isolated archive installation, CLI invocation, and Plugin E2E pass. Independent review corrected the wet/electrical washer-fault boundary before the final run. Work remains only to commit/push, open the stacked PR, and wait for dual-platform CI.

Remote checkpoint: PR #11 is open and `CLEAN`; implementation HEAD `e290fdf` passed Ubuntu in 23 seconds and Windows in 1 minute 51 seconds. PR #7 and PR #9 remain open, `main` and v0.1.1 remain unchanged, and the final documentation-only HEAD is rechecked before handoff.

## v0.2.0 · 会过日子 Human Skills launch

Remote baseline verified before this package: PR #7 is squash-merged to `main` at `2167dcb`; PR #11 is merged into PR #9; PR #9 remains open/dirty at `8d271f6` with green Ubuntu/Windows CI; v0.1.1 remains published. Branch `codex/v0.2.0-human-skills-release` starts from current main.

### Phase 28: prove a clean integration baseline

- [x] Fetch explicit remote refs and map the squash-induced PR #9 ancestry conflict.
- [x] Apply only the net tree delta from main to PR #9 as integration commit `3c9e6ab`, excluding duplicate PR #7 history.
- [x] Prove `HEAD^{tree}` and PR #9 head tree are both `764fe2f074b36a6c318b3d1655620699d5abc653`, with zero tree diff and a passing repository validator.

### Phase 29: launch the bilingual public brand

- [x] Rewrite `README.md` as the Simplified-Chinese-first “会过日子 · Human Skills” homepage and preserve a full English `README.en.md`, with reciprocal language links and user-first examples/install flow.
- [x] Move engineering metrics and campaign history to `docs/engineering-status.md` without deleting evidence or historical reports.
- [x] Add bilingual `SKILLS.md` covering all 17 stable capabilities, user tasks, examples, safety boundaries, Plugin grouping, and release state without copying Skill bodies.
- [x] Update the three life Plugin UI manifests and repo marketplace display copy to Chinese-first bilingual metadata while keeping plugin IDs, Skill folders, and canonical capability IDs stable.
- [x] Add `CHANGELOG.md`, v0.2.0 release notes, and GitHub-facing description/topic metadata; keep copy in “upcoming release” state until remote publication succeeds.

### Phase 30: version and close all launch gates

- [x] Make v0.2.0 the single release version across pyproject, builders, 11 Plugin manifests, marketplace, fixtures, archives, docs, and validation; preserve historical v0.1.1 tag/Release.
- [x] Create an isolated validator environment, install validator-only dependencies, and run official Skill validation for all 17 Skills plus official Plugin validation for all 11 Plugins. Missing validator/dependency access is a release blocker.
- [x] Add RED/GREEN checks for bilingual README/catalog/marketplace/version consistency and release asset inventory.
- [x] Run 146+ tests, 17 evals, repository validator, SQLite benchmark, migration/status/no-op, secrets/license/source checks, two deterministic builds, archive/checksum verification, isolated source install/CLI call, and all 11 Plugin installs/E2E.
- [x] Complete five-axis independent review and resolve every Required/Critical finding before submission.

Final local checkpoint on 2026-08-31: 152 tests, 17 evals, 17/17 official Skill validations, 11/11 official Plugin validations, repository validator, 1,000-record SQLite benchmark, five public-document link checks, and `git diff --check` pass. Two reviewed builds each contain 12 ZIP archives plus `SHA256SUMS.txt`; names and hashes are identical, all 12 checksum entries pass, the source installs and invokes from isolation, and all 11 Plugin archives install and pass E2E. Review fixed the schema-authority/path documentation and added aggregate distribution-file/byte limits before reporting no Required/Critical findings. Historical query/semantic/stable-source no-op evidence remains validator-rebuildable; the current semantic export is no-op, while reusing the old full-campaign cycle truthfully exposes one newly eligible query after the Daily Life Topic Bank expansion and is not claimed as no-op.

### Phase 31: PR, merge, publish, and remote verification

- [x] Open one main-based PR titled `release: launch 会过日子 Human Skills v0.2.0`, documenting PR #9 supersession, tree-equivalence proof, validation, rollback, 17 Skills/11 Plugins/63 scenarios, and release plan.
- [x] Wait for final Ubuntu/Windows CI, merge only when every local/remote gate is green, then read back main merge SHA and close PR #9 as superseded without deleting history.
- [x] Update repository description/topics, create annotated `v0.2.0`, publish bilingual non-draft/non-prerelease Release, upload source + 11 Plugin archives + `SHA256SUMS`, and enable immutable Release only through the verified existing workflow.
- [x] Re-download every published asset, verify checksums/targets/contributors/main CI/v0.1.1 preservation, install source and all Plugins from Release assets, and execute CLI plus critical Skill/E2E calls.

Remote completion checkpoint on 2026-08-31: PR #12 merged as `ef4bd07`; its tree matches the locally verified release tree, and main CI run 33368616448 passed Ubuntu/Windows. PR #9 closed as superseded with history preserved. The annotated `v0.2.0` tag points to `ef4bd07`; Release 379579317 is public, latest, non-draft, non-prerelease, and immutable. All 13 assets were downloaded, byte/checksum/server-digest matched, and appeared in GitHub's signed Release attestation. The downloaded source and 11 Plugins passed install/CLI/E2E, and the downloaded Release Evidence Skill returned `complete` with every gate passing. Repository metadata is bilingual, v0.1.1 remains immutable, and the final evidence is stored in `runs/2026-08-31T07-43-48Z-v0.2.0-attestation.*`.

Rollback: stop promotion and use a reviewed revert/fix PR for serious post-release issues. Never rewrite or delete the published tag/Release to conceal a defect.

## Product-boundary correction after Skills for Humans v0.1.0

The user clarified that Human Runtime content is a separate frontstage product, not an AI-guided lifestyle brand for this repository. KanadeK/skills-for-humans is now public at v0.1.0 with 15 bilingual Human Skills. The Harvester v0.2.0 tag and Release remain immutable historical evidence and are not rewritten.

### Phase 32: restore the backend engine identity

- [x] Start codex/restore-harvester-engine-identity from clean main f3ca131.
- [x] Add RED/GREEN regression coverage for an engine-first Chinese/English README, direct Skills for Humans handoff, preserved historical-prototype wording, and technical repository metadata.
- [x] Replace the mistaken lifestyle storefront with the discovery → evidence → deduplication → supervised decision → validation → maintenance engine boundary.
- [x] Keep v0.2.0 Skills, Plugins, reports, SQLite state, tag, and Release unchanged as historical technical prototype and regression evidence.
- [x] Run the complete tests, evals, repository validator, build/install checks, link checks, and git diff --check.
- [x] Open a documentation-only PR, wait for Ubuntu/Windows CI, review and merge.
- [x] Update the public GitHub description/topics to the committed engine metadata; do not create a Harvester tag or Release.

Success means the first screen routes human-facing readers to Skills for Humans and technical maintainers to the Harvester pipeline without deleting history or introducing another runtime authority.

Local correction checkpoint: 153 tests, 17 evals, repository validator, source/11-Plugin build and isolated E2E, focused identity regressions, README local links, and diff checks pass. Five-axis review found no Required/Critical issue. The diff changes only two READMEs, repository metadata, tests, and persistent task records; no runtime code, SQLite state, Skill, Plugin, version, tag, or Release content changes.

Remote correction checkpoint: documentation PR #14 merged as a613771. Main CI run 33749159337 passed Ubuntu (job 100628475831) and Windows (job 100628475519). The public description and nine technical topics match .github/repository-metadata.json. v0.2.0 remains the unchanged historical Release, and no new Harvester tag or Release was created.
