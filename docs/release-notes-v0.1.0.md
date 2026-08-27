# Codex Skill Harvester v0.1.0

The first release delivers one complete vertical slice from changed public evidence to a reviewed, installable Codex Plugin Skill.

The harvester tracks sources and cursors in Git, extracts facts without persisting raw pages, normalizes full capability fingerprints, recommends exact/semantic/update/new outcomes, and requires an explicit Codex decision before publication. Re-running an unchanged successful source selection produces a truthful no-op.

The included **GitHub Release Evidence** Plugin audits an already-published GitHub release without mutation. Its Skill separates remote repository, PR/check, tag, Release/asset, isolated installation, and contributor evidence from plans or local-only checks.

Release assets:

- complete source archive;
- standalone Plugin archive;
- checksum manifest.

Known limitation: the GitHub repository discovery source follows a moving `sort=updated` result window, so true upstream churn can prevent an immediate all-source no-op even though unchanged entries are not reprocessed. Authentication supports either process-scoped `GITHUB_TOKEN` for `api.github.com` or the official `gh` keyring without exporting its token. Eighty-nine discoveries remain intentionally pending for later reviewed scan rounds.
