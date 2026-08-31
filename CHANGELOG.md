# Changelog

## Unreleased

## 0.2.0 - 2026-08-30

### Added

- Added 9 个 Daily Life Skills in three bilingual, task-domain Plugins for groceries, laundry, and home cooking, with 63 resolved plan/live/recovery scenarios.
- Added seven new software workflow Skills and updated GitHub Release evidence, bringing the catalog to 17 Skills in 11 Plugins.
- Added bilingual public READMEs, a complete Skill catalog, engineering handoff, and repository discovery metadata.
- Added a content-driven Evidence Pack and semantic-batch workflow, Domain × Intent query rotation, five queues, supervised L4 decisions, and compact rebuildable campaign reports.

### Changed

- Replaced runtime Git-JSON authority with one SQLite v4 store for observations, candidates, queues, decisions, batches, checkpoints, and cursors; Git remains authoritative for published artifacts and review history.
- Reframed the project as 会过日子 · Human Skills while retaining codex-skill-harvester as the stable repository and package identifier.
- Made explicit campaign objectives, rather than an empty processing batch, authoritative for completion.
- Expanded the measured production campaign to 204 executable endpoints and 1,622 completed unique queries without treating output counts as quotas.

### Fixed

- Prevented raw registry/package observations and manually seeded workflow_signal hints from impersonating normalized candidates.
- Connected topic provenance and bounded L2/L3 recall to the real candidate pipeline and pushed stable queue pagination into SQLite.
- Required Python Trusted Publishing OIDC permission on the publishing job itself, rejecting matching text in top-level permissions, env, steps, comments, or other jobs.
- Preserved canary/ramp failures as resumable campaign checkpoints and aligned generated reports, validators, and stage-owned metrics.

### Security

- Added bounded archive-member, metadata, RECORD, and overall inspection limits for untrusted Python distributions without extracting or executing package code.
- Kept medical, legal, financial, credential-heavy, high-privilege, and real-world-control capabilities blocked from automatic publication.
- Continued treating all external content as untrusted data; unknown-license page bodies stay in temporary caches and third-party scripts are never executed.

## 0.1.1 - 2026-08-27

- Separated moving GitHub search-window churn from material repository identity changes, preserving new discoveries without revision-only duplicates.
- Added durable status and review-queue CLI views for operator handoff.
- Reviewed the complete 104-item maintenance queue, leaving all 110 repository candidates with explicit decisions and no pending items.
- Updated the GitHub Release evidence Skill with an optional immutable Release gate sourced from official GitHub REST evidence.
- Added a weekly/manual review-only scan workflow, Dependabot configuration, security policy, issue forms, pull request guidance, and validation for those contracts.

## 0.1.0 - 2026-08-27

- Added transactional incremental document, JSON-list, and Atom scanning with persisted cursors and no-op detection.
- Added fixed source trust/license metadata and optional GitHub API authentication without token persistence.
- Added deterministic exact deduplication, capability fingerprint normalization, and Codex-reviewed create/merge/update/legacy-discard decisions; legacy discard records are retained and now report as not promoted.
- Generated the original github-release-evidence Plugin and audit-github-release Skill from real official sources.
- Added trigger reviews, end-to-end evidence checking, repository consistency/security validation, deterministic archives, isolated install/call verification, and Windows/Linux CI.
