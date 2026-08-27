# Initial delivery report — 2026-08-27T09:58:31Z

Status: **ready for remote CI**, not yet published.

## Results

- Real discoveries: 20 from 11 successfully scanned public sources.
- Incremental proof: `2026-08-27T09-26-05Z` changed with 20 discoveries; after one recorded TLS timeout, `2026-08-27T09-27-31Z` completed with `status=no_op` and 0 discoveries.
- Decisions: 3 discarded, 1 merged, 1 updated, 1 created, 14 pending.
- Created capability: `github-release-evidence:audit-github-release`, revision 2.
- External semantic duplicate proof: `openai:gh-fix-ci` matched and was rejected rather than republished.

## Sources

The successful 11-source selection covered official OpenAI Skill/Plugin docs, Codex Release Atom, GitHub CLI/REST docs, and two representative official Skills. `openai-plugin-catalog` and `github-agent-skills-search` remain registered but their anonymous GitHub API requests hit a shared-IP 403. Optional `GITHUB_TOKEN` support is implemented, host-restricted, non-persistent, and tested; a live authenticated scan remains outstanding.

## Validation

- 28 unit/integration tests passed.
- Official Skill and Plugin validators passed.
- Trigger review passed: 3 positive and 4 negative cases.
- End-to-end release evidence passed 8 gates; mismatched PR/tag commits and Markdown newline injection are covered.
- Repository consistency passed: 13 sources, 20 candidates, 6 applied decision records, 1 Plugin, 1 Skill, 0 secret-like findings.
- Deterministic source/Plugin ZIP builds matched across consecutive builds.
- The source ZIP installed and invoked `skill-harvester --help` from an isolated temporary directory.
- Five-axis review repaired run-report collisions, broad exception capture, missing PR/tag alignment, and unsafe Markdown row rendering.

## Content and security

No raw source body, external executable script, credential, private data, copied external Skill body, or unauthorized material is committed. External content was treated only as untrusted data and was never executed.

## Outstanding before v0.1.0

- Live-authenticate and scan the two GitHub API sources.
- Create the public repository and feature PR; wait for Windows/Ubuntu CI and merge.
- Create the annotated tag and Release with all assets.
- Install/call from the published asset and repo marketplace, then verify remote contributors.
- Append a post-publication verification report. Fourteen discoveries remain for later scan rounds and do not block v0.1.0.
