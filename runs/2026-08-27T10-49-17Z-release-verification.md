# v0.1.0 publication verification — 2026-08-27T10:49:17Z

Status: **published and verified**.

## Remote publication

- Public repository: <https://github.com/KanadeK/codex-skill-harvester>, default branch `main`.
- PR #1 delivered the initial vertical slice. PR #2 delivered authenticated API scanning; its Ubuntu and Windows checks passed before squash merge.
- The PR #2 merge commit and the release commit are both `b3190bf21a0487a55b1e3a16836f1bc201abfe87`. The merged `main` CI run `33063492658` passed.
- `v0.1.0` is an annotated tag object `9f16d05d1074df9567d30cdb2dfdd9769cf56b3c` resolving to the same commit.
- The GitHub Release is published, reports `isImmutable=true`, and passes `gh release verify` against GitHub's attestation.

## Published assets

All three assets were downloaded again from the public Release and passed `gh release verify-asset`:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `codex-skill-harvester-v0.1.0.zip` | 166234 | `11a4a61094f1dd125340a5374bb1d74abc0204b9d60e581571134102e8a1f6f8` |
| `github-release-evidence-v0.1.0.zip` | 5478 | `04033ceb83168da51850eb4ba437fa96b9436d960dd1b7ba10f59271a34a51a2` |
| `SHA256SUMS.txt` | 200 | `779b6900f5362f86084f66716a2286dac3138bbe0687316d5cf583536354090b` |

## Installation and live invocation

- The downloaded source archive installed with no dependency download, invoked `skill_harvester --help`, and passed its repository validator in an isolated temporary directory.
- The published marketplace manifest resolves to `codex-skill-harvester`; the downloaded `github-release-evidence` Plugin passed the official Plugin validator.
- The released Plugin's `check_snapshot.py` was invoked against the live public repository, PR #2, both CI checks, tag, all expected assets, the isolated installation result, and remote contributors. Its committed audit result is `complete` with all eight gates passing.

## Harvest outcome

- 13 registered sources and 13 successful persisted source states.
- 95 candidates: 6 applied and 89 pending.
- Applied decisions: 3 discard, 1 merge, 1 update, and 1 create.
- Stable-source proof remains 20 changed discoveries followed by a zero-discovery no-op. Authenticated API proof remains 63 initial discoveries followed by only 2 true search changes while the official Plugin catalog produced zero.

## Identity and content safety

GitHub reports one contributor, `KanadeK`, with three main-branch contributions. The full local history has zero `Co-authored-by` trailers and uses the same GitHub noreply account. No credential, raw source body, external executable script, copied third-party Skill body, or secret-like material is present in the repository.

## Non-blocking continuation state

Eighty-nine candidates remain pending explicit semantic review for later “scan again” rounds. The GitHub repository discovery query intentionally follows a moving `sort=updated` window; real upstream churn may therefore produce a small changed-only batch instead of an all-source no-op.
