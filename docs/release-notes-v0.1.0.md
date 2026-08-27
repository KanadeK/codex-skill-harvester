# Codex Skill Harvester v0.1.0

The first release delivers one complete vertical slice from changed public evidence to a reviewed, installable Codex Plugin Skill.

The harvester tracks sources and cursors in Git, extracts facts without persisting raw pages, normalizes full capability fingerprints, recommends exact/semantic/update/new outcomes, and requires an explicit Codex decision before publication. Re-running an unchanged successful source selection produces a truthful no-op.

The included **GitHub Release Evidence** Plugin audits an already-published GitHub release without mutation. Its Skill separates remote repository, PR/check, tag, Release/asset, isolated installation, and contributor evidence from plans or local-only checks.

Release assets:

- complete source archive;
- standalone Plugin archive;
- checksum manifest.

Known limitation: anonymous GitHub API requests can be rate-limited. `GITHUB_TOKEN` is supported for `api.github.com` only and is never stored. Fifteen first-round discoveries remain intentionally pending for later reviewed scan rounds.
