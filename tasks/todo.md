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

- [ ] Acceptance: public remote, merged PR, green CI, annotated tag, Release assets, installation/call proof, and contributor evidence are current and consistent.
- [ ] Verify: GitHub read-back plus clean temporary extraction.
- [ ] Files: release notes, final run report, Git history and remote objects.
- Dependencies: Task 5 and completed code review.
