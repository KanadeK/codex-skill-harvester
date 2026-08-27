# Evidence contract

Use this normalized JSON shape as input to `scripts/check_snapshot.py`. Values must come from the read-only commands in `SKILL.md`; omitted proof is represented by `null`, not by a guessed default.

```json
{
  "repository": {
    "name_with_owner": "OWNER/REPO",
    "is_private": false,
    "default_branch": "main",
    "url": "https://github.com/OWNER/REPO"
  },
  "release": {
    "tag_name": "v1.0.0",
    "is_draft": false,
    "published_at": "RFC-3339 timestamp",
    "url": "https://github.com/OWNER/REPO/releases/tag/v1.0.0",
    "target_commit_sha": "full commit SHA",
    "asset_names": ["artifact.zip"]
  },
  "tag": {
    "name": "v1.0.0",
    "commit_sha": "full commit SHA"
  },
  "expected_assets": ["artifact.zip"],
  "pull_request": {
    "number": 1,
    "state": "MERGED",
    "merge_commit_sha": "full commit SHA",
    "url": "https://github.com/OWNER/REPO/pull/1",
    "checks": [{"name": "test", "bucket": "pass"}]
  },
  "installation": {
    "command": "documented acceptance command",
    "exit_code": 0,
    "observed_output": "short factual result"
  },
  "contributors": [{"login": "contributor"}]
}
```

`pull_request` and `installation` may be `null`; their gates then remain `NOT_CHECKED`. When a pull request is present, its `merge_commit_sha` must equal `tag.commit_sha`. An empty `expected_assets` list means the audit makes no custom-asset claim.

## Authority sources

- GitHub CLI repository view: https://cli.github.com/manual/gh_repo_view
- GitHub CLI pull-request checks: https://cli.github.com/manual/gh_pr_checks
- GitHub CLI release view: https://cli.github.com/manual/gh_release_view
- Authenticated GitHub API access: https://cli.github.com/manual/gh_api
- GitHub REST releases: https://docs.github.com/en/rest/releases/releases
- GitHub REST repositories: https://docs.github.com/en/rest/repos/repos
