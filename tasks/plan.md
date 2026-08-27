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
- [ ] Perform a five-axis code review and repair all required findings.
- [ ] Commit exact paths in atomic increments and verify author/co-author hygiene.
- [ ] Create the public repository, push the branch, open a PR, wait for green CI, merge, tag v0.1.0, and create the Release.
- [ ] Verify release assets from a clean temporary extraction, marketplace/plugin discovery, CLI invocation, remote contributor list, and final run report.

### Checkpoint: published

- [ ] Public remote, merged PR, green CI, immutable tag, Release assets, installation/call path, and contributor evidence all agree on the same release commit.
- [ ] Local child worktree is clean; outer workspace remains uncommitted.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Official formats drift | Generated artifacts become invalid | Keep format authority sources in the registry and validate every run/CI |
| GitHub rate limits or network failure | Live scan cannot complete | Conditional requests, bounded source subset, transactional state, honest failed report |
| Prompt injection in fetched text | Scope or tool misuse | Treat bodies as data, use deterministic extractors, never execute or obey source text |
| License ambiguity | Unauthorized redistribution | Store license status and block copying; synthesize original factual workflows only |
| Semantic false positive | Useful skill incorrectly merged/rejected | Require an explicit Codex decision with compared fingerprints and rationale |
| GitHub authentication expires | Publication blocks after local success | Re-authenticate only through official `gh auth login -h github.com -p https -w` when needed |

## Open questions

None for the first vertical slice.
