# Evidence contract

Use this normalized JSON shape as input to `scripts/check_snapshot.py`. Values must come from the read-only commands in `SKILL.md`; omitted proof is represented by `null`, not by a guessed default.

```json
{
  "requirements": {
    "immutable_release": true,
    "asset_attestations": true
  },
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
    "immutable": true,
    "url": "https://github.com/OWNER/REPO/releases/tag/v1.0.0",
    "target_commit_sha": "full commit SHA",
    "asset_names": ["artifact.zip"]
  },
  "tag": {
    "name": "v1.0.0",
    "commit_sha": "full commit SHA"
  },
  "expected_assets": ["artifact.zip"],
  "attestations": [
    {
      "asset_name": "artifact.zip",
      "release_tag": "v1.0.0",
      "verified": true,
      "verified_owner": "OWNER",
      "source_url": "https://github.com/OWNER/REPO/attestations"
    }
  ],
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

`pull_request` and `installation` may be `null`; their gates then remain `NOT_CHECKED`. When a pull request is present, its `merge_commit_sha` must equal `tag.commit_sha`. An empty `expected_assets` list means the audit makes no custom-asset claim. Set `requirements.immutable_release` to `true` only when immutable Release proof is part of the stated acceptance criteria; then `release.immutable` must come from the REST Release record and be `true`. Set `requirements.asset_attestations` to `true` only when provenance is required; every expected asset must then have a successful read-only `gh release verify-asset TAG FILE --format json` result in `attestations`, and its `release_tag` must equal `release.tag_name`. An attestation is not a malware or correctness verdict.

## Authority sources

- GitHub CLI repository view: https://cli.github.com/manual/gh_repo_view
- GitHub CLI pull-request checks: https://cli.github.com/manual/gh_pr_checks
- GitHub CLI release view: https://cli.github.com/manual/gh_release_view
- Authenticated GitHub API access: https://cli.github.com/manual/gh_api
- GitHub REST releases: https://docs.github.com/en/rest/releases/releases
- GitHub REST repositories: https://docs.github.com/en/rest/repos/repos
- GitHub artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations
- GitHub CLI release asset verification: https://cli.github.com/manual/gh_release_verify-asset
