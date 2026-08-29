# Changelog

## Unreleased

- Defined a measured three-layer scale architecture, versioned primary-family/facet taxonomy, schema migration policy, and explicit triggers for evaluating indexed storage.
- Added stable canonical capability IDs independent from Plugin/Skill packaging, retained `not_promoted` decisions with reactivation conditions, and normalized legacy `discard` reporting without deleting records.
- Added priority-ordered, bounded, resumable review pages and stage-owned discovery metrics.
- Added a temporary-directory JSON lifecycle benchmark and a small cross-platform CI exercise without changing the released v0.1.1 artifacts.

## 0.1.1 - 2026-08-27

- Separated moving GitHub search-window churn from material repository identity changes, preserving new discoveries without revision-only duplicates.
- Added durable `status` and `review-queue` CLI views for operator handoff.
- Reviewed the complete 104-item maintenance queue, leaving all 110 repository candidates with explicit decisions and no pending items.
- Updated the GitHub Release evidence Skill with an optional immutable Release gate sourced from official GitHub REST evidence.
- Added a weekly/manual review-only scan workflow, Dependabot configuration, security policy, issue forms, pull request guidance, and validation for those contracts.

## 0.1.0 - 2026-08-27

- Added transactional incremental document, JSON-list, and Atom scanning with persisted cursors and no-op detection.
- Added fixed source trust/license metadata and optional GitHub API authentication without token persistence.
- Added deterministic exact deduplication, capability fingerprint normalization, and Codex-reviewed create/merge/update/legacy-discard decisions; legacy discard records are retained and now report as not promoted.
- Generated the original `github-release-evidence` Plugin and `audit-github-release` Skill from real official sources.
- Added trigger reviews, end-to-end evidence checking, repository consistency/security validation, deterministic archives, isolated install/call verification, and Windows/Linux CI.
