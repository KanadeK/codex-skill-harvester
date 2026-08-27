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

- [ ] Acceptance: moving search-window churn is reported separately and does not create revision-only duplicate candidates; status and review queue are directly inspectable.
- [ ] Verify: focused source and CLI tests cover revision-only change, reordering, new items, status output, and queue filtering.
- [ ] Files: source state/CLI modules, registry, tests, specification, and operator docs.
- Dependencies: Task 6.

## Task 8: review the inherited queue and update useful capability evidence

- [ ] Acceptance: all 89 pending discoveries have explicit records; no title-only or unknown-license signal becomes a Skill; any update is original and source-traceable.
- [ ] Verify: zero pending candidates, repository consistency, Skill format, trigger cases, and end-to-end evidence checker pass.
- [ ] Files: candidate status, decision records, catalog, selected Plugin Skill/evals, and run report.
- Dependencies: Task 7.

## Task 9: automate and harden maintenance

- [ ] Acceptance: scheduled/manual scans can open changed-only PRs without semantic publication; security/community metadata and remote protections are active.
- [ ] Verify: workflow contract tests, remote API read-back, required CI, and unused-surface settings agree.
- [ ] Files: `.github/*`, security/community documents, validator/tests, and remote repository settings.
- Dependencies: Task 8.

## Task 10: publish and verify v0.1.1

- [ ] Acceptance: reviewed PR, green CI, immutable tag/Release, deterministic assets, isolated install/CLI, released Skill invocation, settings, and contributors are verified.
- [ ] Verify: local release gates plus remote attestation and final report.
- [ ] Files: changelog, release notes, final report, Git history, tag, and Release assets.
- Dependencies: Task 9 and completed code review.
