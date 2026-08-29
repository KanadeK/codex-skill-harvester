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
- [ ] Files: runtime store plus existing callers, migration ADR/manifest, one exercised campaign policy, fixtures/tests, and harvest workflow.
- Dependencies: Task 16 and a new total-control authorization.

## Task 18: execute the first high-throughput campaign canary

- [x] Acceptance: official OpenAI format, GitHub delivery, and Python packaging source groups ran as a three-source structural canary; 10 safe endpoints then completed with persisted counters and Usage `measured=false`. The future 5–10% full-inventory condition remains an explicit expansion gate, not a false completion claim.
- [x] Verify: unchanged-source no-op and failed-ramp checkpoint fixtures pass; normal stop-loss metrics permitted continuation to the currently registered safe capacity without automatic publication, merge, or Release.
- [x] Files: SQLite runtime state, source registry/policy, run reports, and reviewed PR material only.
- Dependencies: Task 17 and green implementation CI.
