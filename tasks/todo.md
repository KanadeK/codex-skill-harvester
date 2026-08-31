# v0.1.0 task checklist

## Task 1: bootstrap durable repository context

- [x] Acceptance: independent child Git root, specification, plan, research, maintainer Skill, and Plugin scaffold exist.
- [x] Verify: repository root and creator validators pass.
- [x] Files: `AGENTS.md`, `docs/*`, `tasks/*`, `.agents/skills/*`, `plugins/*`.
- Dependencies: none.

## Task 2: implement transactional incremental scans

- [x] Acceptance: changed sources emit discoveries; unchanged sources emit no-op; failed selection does not advance state.
- [x] Verify: focused source/state tests pass.
- [x] Files: source/state modules plus their tests and fixtures.
- Dependencies: Task 1.

## Task 3: implement reviewed capability decisions

- [x] Acceptance: exact, semantic, update, and new fixtures receive distinct recommendations and explicit outcomes.
- [x] Verify: focused decision/catalog tests pass.
- [x] Files: decision/catalog modules plus their tests and fixtures.
- Dependencies: Task 2.

## Task 4: generate and validate one real Plugin Skill

- [x] Acceptance: an original source-traceable GitHub Release audit Skill is created from a reviewed decision.
- [x] Verify: format, positive/negative trigger, and end-to-end evals pass.
- [x] Files: one plugin skill, catalog/decision records, evals, real run report.
- Dependencies: Task 3.

## Task 5: automate repository and release gates

- [x] Acceptance: local validator, release builder, security/material checks, and CI cover the required structure and behavior.
- [x] Verify: full tests, validation, build, isolated archive invocation, and initial remote CI pass.
- [x] Files: `scripts/*`, `.github/workflows/*`, release docs.
- Dependencies: Task 4.

## Task 6: publish and verify v0.1.0

- [x] Acceptance: public remote, merged PR, green CI, immutable annotated tag, Release assets, installation/call proof, and contributor evidence are current and consistent.
- [x] Verify: GitHub attestation read-back plus clean temporary extraction and released-Skill invocation.
- [x] Files: release notes, final run report, Git history and remote objects.
- Dependencies: Task 5 and completed code review.

## Task 7: stabilize recurring scans

- [x] Acceptance: moving search-window churn is reported separately and does not create revision-only duplicate candidates; status and review queue are directly inspectable.
- [x] Verify: focused source and CLI tests cover revision-only change, reordering, new items, status output, and queue filtering.
- [x] Files: source state/CLI modules, registry, tests, specification, and operator docs.
- Dependencies: Task 6.

## Task 8: review the inherited queue and update useful capability evidence

- [x] Acceptance: all 89 pending discoveries have explicit records; no title-only or unknown-license signal becomes a Skill; any update is original and source-traceable.
- [x] Verify: zero pending candidates, repository consistency, Skill format, trigger cases, and end-to-end evidence checker pass.
- [x] Files: candidate status, decision records, catalog, selected Plugin Skill/evals, and run report.
- Dependencies: Task 7.

## Task 9: automate and harden maintenance

- [x] Acceptance: scheduled/manual scans can open changed-only PRs without semantic publication; security/community metadata and remote protections are active.
- [x] Verify: workflow contract tests, remote API read-back, required CI, and unused-surface settings agree.
- [x] Files: `.github/*`, security/community documents, validator/tests, and remote repository settings.
- Dependencies: Task 8.

## Task 10: publish and verify v0.1.1

- [x] Acceptance: reviewed PR, green CI, immutable tag/Release, deterministic assets, isolated install/CLI, released Skill invocation, settings, and contributors are verified.
- [x] Verify: local release gates plus remote attestation and final report.
- [x] Files: changelog, release notes, final report, Git history, tag, and Release assets.
- Dependencies: Task 9 and completed code review.

## Task 11: document the measured scale architecture

- [x] Acceptance: the repository defines the three product layers, measured current limits, explicit migration triggers, and a phased roadmap without claiming projected volume as a KPI.
- [x] Verify: documentation references the same thresholds as the machine-readable scale policy.
- [x] Files: `docs/architecture.md`, `docs/scale-audit.md`, `docs/roadmap.md`, `docs/decisions/*`, `config/scale-policy.json`.
- Dependencies: Task 10.

## Task 12: version taxonomy and schema migration

- [x] Acceptance: every current catalog capability has one stable canonical id, one primary family, validated facets, aliases/variants/merged evidence fields, and taxonomy/schema versions.
- [x] Verify: focused taxonomy and v1-to-v2 migration fixtures pass; repository validation rejects drift.
- [x] Files: `catalog/taxonomy.json`, `catalog/capabilities.json`, taxonomy/migration modules, fixtures, and tests.
- Dependencies: Task 11.

## Task 13: make non-promotion and review batching explicit

- [x] Acceptance: legacy `discard` records display as `not_promoted`; new v2 non-promotion decisions require reactivation conditions; queue pages are priority ordered, bounded, and resumable.
- [x] Verify: focused decision/reporting/CLI tests prove compatibility, failure paths, and cursor continuation.
- [x] Files: decision/reporting/CLI modules and tests.
- Dependencies: Task 12.

## Task 14: add stage-owned observability and scale benchmark

- [x] Acceptance: scan reports contain measured source/enqueue/duplicate metrics, and a reproducible temporary benchmark inventories, projects, and evaluates the active backend.
- [x] Verify: changed/no-op/failure fixtures and benchmark tests pass without external network or persistent fixture output.
- [x] Files: source/scaling modules, benchmark script, policy, CI, and tests.
- Dependencies: Tasks 12 and 13.

## Task 15: review and open the scale-foundation PR

- [x] Acceptance: all local gates pass, exact-path commits are pushed, one PR is open with green CI, and no merge, tag, Release, broad scan, or other-repository change occurs.
- [x] Verify: local/remote branch SHA, PR status, CI jobs, clean worktree, and absent Release change are read back.
- [x] Files: change summary and Git/GitHub objects only.
- Dependencies: Task 14 and completed five-axis review.

## Task 16: adopt the bounded scale route

- [x] Acceptance: the complete external planning input is classified as adopted, modified, deferred, or rejected against the merged runtime and controller decisions; every deferred boundary has an entry condition and one authority.
- [x] Verify: `docs/plan-adoption-audit.md` distinguishes confirmed facts, assumptions, measurement prerequisites, and explicit exclusions; repository validation remains green.
- [x] Files: `docs/plan-adoption-audit.md`, roadmap, and task records only.
- Dependencies: Task 15 and merged PR #6.

## Task 17: implement the first calibration vertical slice

- [x] Acceptance: a one-time validated importer atomically converts active JSON runtime state to SQLite, then scan/review/apply/validation use only SQLite while Git retains published artifacts and readable manifests.
- [x] Verify: fixtures cover successful import, failed import preservation, JSON independence after cutover, duplicate levels, continuation, queue placement, and no-op; full CI passes.
- [x] Files: runtime store plus existing callers, migration ADR/manifest, one exercised campaign policy, fixtures/tests, and harvest workflow.
- Dependencies: Task 16 and a new total-control authorization.

## Task 18: execute the first high-throughput campaign canary

- [x] Acceptance: official OpenAI format, GitHub delivery, and Python packaging source groups ran as a three-source structural canary; 10 safe endpoints then completed with persisted counters and Usage `measured=false`. The future 5–10% full-inventory condition remains an explicit expansion gate, not a false completion claim.
- [x] Verify: unchanged-source no-op and failed-ramp checkpoint fixtures pass; normal stop-loss metrics permitted continuation to the currently registered safe capacity without automatic publication, merge, or Release.
- [x] Files: SQLite runtime state, source registry/policy, run reports, and reviewed PR material only.
- Dependencies: Task 17 and green implementation CI.

The Task 18 candidate-yield interpretation was invalidated by controller review: that run acquired useful evidence but treated every observation as a candidate. Task 19 below is the current authority; Task 18's old counts must not be used as normalized-candidate evidence.

## Task 19: repair PR #7's observation-to-candidate boundary

- [x] Acceptance: package/registry/release signals remain observations unless explicit workflow normalization produces a seven-field candidate; official trust alone cannot select `official-gap`.
- [x] Acceptance: source group/topic, L2 exact fingerprint lookup, L3 bounded recall, and all five queues execute on the real source path.
- [x] Acceptance: campaign checkpoints canary/ramp errors and request/byte/store/workload stop-loss before more work; scheduled automation uses campaign.
- [x] Acceptance: campaign metrics distinguish raw observations, inserted/duplicate observations, normalized/duplicate candidates, L3 recalls, pending queue, and unmeasured deep review/Usage.
- [x] Acceptance: SQLite review pagination uses indexed database ordering/cursor/LIMIT and status uses SQL aggregation.
- [x] Verify: controlled tests cover the complete funnel, L2/L3, all queues, no-op, changed PyPI, every required checkpoint, bounded pagination/query plan, migration preservation, and forged metrics.
- [x] Files: PR #7 schema-2 separation base, source/campaign/reporting/validation call paths, policies, workflow, fixtures, and synchronized authority documents; Task 20 advances the runtime authority to schema 3.
- [x] Verify: corrected real campaign, complete local gates, clean verification behavior, and five-axis review are complete.
- [x] Submit: exact commits were pushed to PR #7 and Ubuntu/Windows CI passed; PR remains open for total-control merge approval, with no tag or Release.
- Dependencies: Task 18 review finding and explicit controller authorization. Do not merge or release.

## Task 20: run the first content-driven production campaign

- [x] Acceptance: `workflow_signal` is hint-only; T0/T1/T2 observations can enter a persisted content-review batch; Evidence Packs and partial progress survive interruption.
- [x] Acceptance: real Topic Bank queries and selected official/primary endpoints expand the executable inventory beyond the inherited 10 endpoints, with query cursor and source utility.
- [x] Acceptance: Codex performs actual evidence reading, normalized candidate extraction, L2/L3, L4, and original synthesis; every qualified Skill passes format, trigger, E2E, isolated install/script, originality, and license gates.
- [x] Verify: stable repeats process only changed evidence or unfinished batches; reports separate queries, requests, bytes, observations, candidates, recalls, deep reviews, decisions, artifacts, failures, Usage measurement, and checkpoints.
- [x] Submit: stacked PR #8 is open against `codex/plan-adoption-audit`; Ubuntu/Windows CI passed and both PRs remain open without tag or Release.
- Dependencies: PR #7 final HEAD `2ea8771cfbc45bb3f52953727eba20244f1f4180` and explicit content-production authorization.

The Task 20 submission line records the state when it was written. PR #8 was subsequently squash-merged into the still-open PR #7 branch on 2026-08-30; `main`, tags, and Releases were unchanged. The correction cannot be appended to the closed PR, so Task 21 is the current stacked repair authority.

## Task 21: correct campaign completion and Python archive/OIDC gates

- [x] Acceptance: the parent campaign has one policy-owned objective and reports `active`, `checkpoint`, or `campaign_completed` independently from the current slice status; 26 endpoints/21 queries and no-op replay cannot complete the parent campaign.
- [x] Acceptance: only the publishing job's own `permissions.id-token: write` passes, while top-level, env, step, comment/string, other-job, and missing placements fail.
- [x] Acceptance: sdist/wheel member count, metadata/RECORD reads, archive size, and declared expanded work are bounded; over-limit fixtures fail at named gates without extraction or execution.
- [x] Verify: focused RED/GREEN regressions, full unittest, evals, validator, deterministic build/install/invocation, official Skill/Plugin validators, and diff checks pass without tracked-state pollution.
- [x] Submit: correction PR #9 is open against `codex/plan-adoption-audit`; its initial correction HEAD passed Ubuntu/Windows CI, PR #7 remains open, and no tag or Release was created. The final documentation-only HEAD is rechecked by CI before Phase 23 starts.
- Dependencies: PR #8 merge commit `d0cb9ef0d79ea254598fe66ee6f47a4dd0e532c3` and the 2026-08-30 controller review.

## Task 22: run the full 2026-08-30 content campaign

- [x] Acceptance: `codex/full-campaign-2026-08-30` starts from Task 21's verified HEAD and is submitted as stacked PR #10 against `codex/pr8-campaign-corrections` rather than expanding the correction PR.
- [x] Acceptance: low-risk Domain × Intent coverage reaches 204 executable endpoints and 1,622 actual queries, exceeding the 180/1,500 capacity lower bound without a stop-loss.
- [x] Acceptance: every measured observation, Evidence Pack, candidate, L3 recall, L4 outcome, and Skill artifact comes from real source/query/semantic work; high-risk and low-trust signals cannot auto-publish.
- [x] Acceptance: tracked campaign evidence stays compact and authoritative, Usage remains `measured=false` without a real meter, and no candidate or Skill count is inflated to meet a capacity direction.
- [x] Verify: 128 unittest cases, eight Skill evals, repository validation, SQLite benchmark, deterministic build/install/invocation, and diff checks pass; the final summary separates coverage, funnel stages, decisions, artifacts, failures/rate limits, Usage, checkpoint, and continuation.
- [x] Submit: PR #10 is open and `CLEAN`; implementation HEAD `59b0734` passed Ubuntu/Windows CI and remains unmerged with no tag or Release. The final documentation-only HEAD is rechecked before handoff.
- Dependencies: Task 21 complete and explicit 2026-08-30 full-campaign authorization.

Completion checkpoint: the branch starts at verified correction HEAD `7aa8f86`; 204 revision-pinned endpoints and 1,622 unique Domain × Intent queries are now executed capacity. The query cycle completed in 1,626 attempts with four recoverable GitHub rate-limit failures, 151 discovery hits, and zero pending work. The sole SQLite authority records 1,204 observations, 168 Evidence Packs, 136 applied decisions, and eight Skills. Eight campaign semantic batches reviewed 217 observations into 58 Evidence Packs and 26 candidates, producing 263 L3 recalls and 26 L4 outcomes: seven creates, three updates, one merge, and 15 `not_promoted`. The final 204-endpoint ramp succeeded without source failures. All local verification gates pass; PR #10 implementation HEAD `59b0734` is `CLEAN` with green Ubuntu/Windows CI. The final documentation-only HEAD is rechecked before handoff.

## Task 23: add Daily Life and close discovery-hit review

- [x] Acceptance: Daily Life is a formal product domain and the three approved families are registered without treating physical places as software ecosystems.
- [x] Acceptance: the seven-field fingerprint has one documented meaning; reality-facing execution environments use registered taxonomy values without a parallel fingerprint schema.
- [x] Acceptance: every query hit has one SQLite lifecycle and one reviewed terminal outcome; query completion reports pending hit review rather than hiding it.
- [x] Acceptance: only a Codex-reviewed, known-license, traceable, non-duplicate, reproducibly scanned endpoint remains in the source registry; partial review, selection failure/reopen, resume, and no-op are exercised.
- [x] Verify: focused RED/GREEN tests cover GitHub/Web hits, pending, partial resume, duplicate recurrence, selected source, invalid license/metadata, failed selection, report conversion metrics, and forged reports.
- [x] Files: taxonomy/spec/architecture, runtime/query/report/CLI/validation paths, focused fixtures/tests, and migrated SQLite authority.
- Dependencies: remote PR #9 HEAD `034a1f01d77e780e60f801f659fc9a8257abba98` and explicit Daily Life authorization.

## Task 24: build and adjudicate the 60-scenario life bank

- [x] Acceptance: 21 scenarios in each family use real Chinese/English sources and end in `create|merge|not_promoted`, with zero pending.
- [x] Acceptance: every scenario records user goal, critical inputs, locality/equipment constraints, observable completion, recovery, safety stop, source refs, and decision linkage.
- [x] Acceptance: 13 selected sources are T1/T2 operational evidence; community demand signals did not support publication.
- [x] Verify: real scans, 12 Evidence Packs, nine candidates, 156 L3 recalls, nine L4 creates, reactivation conditions, region/language distribution, and 72.2222% selected-hit conversion are validator-reconstructible.
- [x] Files: source registry/context, 63-scenario bank, SQLite state, compact evidence/decision reports, and no raw page bodies.
- Dependencies: Task 23.

## Task 25: produce and evaluate Daily Life Plugins

- [x] Acceptance: nine qualified independent capabilities are original and packaged into exactly three small installation-intent Plugins; 45 neighboring scenarios merge into canonical capabilities rather than cloned Skills.
- [x] Acceptance: all nine Skills are instruction-only and do not claim physical completion, guess missing facts, universalize local practice, cross into medical nutrition/dangerous repair, or require invented scripts.
- [x] Acceptance: descriptions include natural Chinese triggers and discriminating exclusions; workflows support planning, live step-by-step operation, and failure recovery.
- [x] Verify: 36 trigger decisions and 27 realistic instruction-only E2E responses pass source/originality/non-overlap/safety behavioral review. Official standalone validators are locally blocked only by their missing PyYAML dependency; repository validation remains authoritative.
- [x] Files: three Plugins, nine Skills, nine eval records, catalog/marketplace, and reviewed decisions.
- Dependencies: Task 24 and skill-creator rules.

## Task 26: validate and submit the Daily Life pilot

- [x] Acceptance: all 63 scenarios are resolved, each family has three useful installable Skills, pending query-hit/semantic/L4 work is zero, and Usage remains `measured=false`.
- [x] Verify: 146 unittest cases, 17 evals, validator, SQLite-v4 benchmark, deterministic source/11-Plugin build, isolated install/invocation, and independent five-axis audit pass without tracked pollution. Official standalone validators are unavailable only because their own local Python environment lacks PyYAML.
- [x] Submit: exact commits are pushed to `codex/daily-life-skills-pilot-2026-08-30`; stacked PR #11 targets `codex/pr8-campaign-corrections`, implementation HEAD `e290fdf` is `CLEAN` with passing Ubuntu/Windows CI, and no PR, tag, or Release is merged or created. The final documentation-only HEAD is rechecked before handoff.
- Dependencies: Tasks 23–25 and no payment/login/high-risk authorization blocker.

## Task 27: integrate the stacked capability tree onto current main

- [x] Acceptance: branch `codex/v0.2.0-human-skills-release` starts from main `2167dcb` and contains only the net PR #9 tree delta as commit `3c9e6ab`.
- [x] Verify: integration tree and PR #9 tree both equal `764fe2f074b36a6c318b3d1655620699d5abc653`; repository validator reports 17 Skills, 11 Plugins, 217 states, 1,217 observations, 180 Evidence Packs, 145 decisions, and 63 scenarios.
- [x] Safety: no force push, reset-hard, ours/theirs conflict swallowing, revived runtime JSON, or dual-write compatibility path.
- Dependencies: merged PR #7, merged PR #11 into open PR #9, and explicit release authorization.

## Task 28: create the bilingual Human Skills storefront

- [ ] Acceptance: Chinese-first `README.md`, complete `README.en.md`, and bilingual `SKILLS.md` present the approved brand, three real examples, installation, 17 Skills/11 Plugins, physical-action boundary, sources/safety/dedupe, and reciprocal language navigation.
- [ ] Acceptance: engineering evidence moves to a linked maintainer document; no report/history is deleted, and no pre-release copy falsely claims v0.2.0 is already published.
- [ ] Acceptance: three life Plugin manifests and marketplace public copy are Chinese-first bilingual while all internal identifiers remain stable.
- [ ] Verify: automated documentation/catalog/manifest/link consistency checks pass.
- Dependencies: Task 27.

## Task 29: prepare and validate v0.2.0

- [ ] Acceptance: one v0.2.0 source of truth drives package, 11 Plugin manifests, archive names, fixtures, checksums, docs, and release notes; v0.1.1 remains untouched and no consumer migration is required.
- [ ] Acceptance: `CHANGELOG.md` records Added/Changed/Fixed/Security for the 9 life Skills, 6 later software Skills, Python/GitHub updates, discovery review, SQLite v4, campaign correction, and bilingual brand.
- [ ] Verify: official quick validator passes all 17 Skills and official Plugin validator passes all 11 Plugins in an isolated dependency environment.
- [ ] Verify: full tests/evals/validator/benchmark/no-op/security, two identical builds, 12 archives + checksums, isolated installs and all Plugin E2E pass; five-axis review has no Required/Critical findings.
- Dependencies: Task 28.

## Task 30: merge and publish v0.2.0

- [ ] Acceptance: one clean PR targets main and explains PR #9 supersession, integration equivalence, brand, inventory, verification, release plan, and rollback.
- [ ] Acceptance: final PR CI passes on Ubuntu/Windows, PR merges, PR #9 closes as superseded, repository description/topics update, and annotated `v0.2.0` points at verified main.
- [ ] Acceptance: public bilingual Release is non-draft/non-prerelease with source archive, 11 Plugin archives, and `SHA256SUMS`; immutable state follows verified repository capability.
- [ ] Verify: assets are re-downloaded, checksums/target/main CI/contributors/v0.1.1 are read back, source and all 11 Plugins install from Release assets, and real CLI/Skill/E2E calls pass.
- Dependencies: Task 29 and explicit user authorization already granted for in-scope GitHub publication.
