# Codex Skill Harvester v0.1.1

This maintenance release makes the harvester ready for recurring operation without turning it into an unattended semantic publisher.

The scanner now separates a moving GitHub search result window from material repository identity. Revision-only updates and reordering remain observable state but do not create duplicate candidates. New repository identities and meaningful title or URL changes remain real discoveries. Read-only `status` and `review-queue` commands expose the persisted cursor, catalog, decision totals, and pending work directly.

The real maintenance round resumed from v0.1.0 state, discovered 15 new items, and reviewed those together with 89 inherited candidates. Its 104 decisions used the then-current schema-1 outcomes: 100 legacy `discard` records, 3 merges, 1 update, and no forced creation. Across the repository, all 110 candidates now have explicit records: 103 are reported as not promoted to independent Skills, 4 merged, 2 updated, and 1 created. No discovery record was deleted.

The existing **GitHub Release Evidence** Plugin remains the only published task domain. Its `audit-github-release` Skill can now require the official REST Release record to prove `immutable: true`; the deterministic checker fails when immutability is required but absent.

A weekly and manually dispatchable GitHub Actions workflow scans from committed cursors and opens a pull request only for actual discoveries. It stages only state, candidate, and run-report paths. It never applies Codex decisions, copies source bodies, executes fetched scripts, or publishes a Skill. Dependabot, security reporting guidance, issue forms, pull request guidance, and repository validation cover the new maintenance surface.

Release assets:

- complete source archive;
- standalone Plugin archive;
- checksum manifest.

Known operational caveat: a large all-source network transaction can time out. Cursor updates remain transactional, and maintainers can retry bounded source subsets without losing the last successful state. A moving search window can also introduce genuinely unseen repositories between close scans; these are correctly reported as discoveries rather than suppressed as churn.
