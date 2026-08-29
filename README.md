# Codex Skill Harvester

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

[v0.1.1](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.1.1) is published as an immutable GitHub Release with verified source, Plugin, and checksum assets. The [final attestation](runs/2026-08-27T14-31-10Z-v0.1.1-attestation.md) records the PR, CI, tag, assets, isolated install, live Skill call, settings, and contributors.

Codex Skill Harvester incrementally turns changed, authoritative public workflow evidence into reviewed, original Codex Skills grouped by user task domain. It persists source cursors, evidence hashes, capability fingerprints, semantic decisions, generated artifacts, and run reports in the repository, so a later scan resumes without chat memory.

It is deliberately not a Skill mirror. Deterministic Python owns fetching, change detection, exact deduplication, state, validation, and packaging. Codex owns semantic comparison and the decision to not promote, merge, update, or create.

The current unreleased scale foundation keeps the Git-JSON backend, adds versioned capability taxonomy and schema migration, bounds review work, and measures when an indexed backend is actually justified. It does not claim that the current backend already supports the long-term capacity envelope.

## What v0.1.1 proves

- 13 registered and live-scanned sources across official OpenAI format authority, vendor documentation, GitHub search/API, Release/Atom, and representative external Skills.
- A real incremental maintenance scan resumed from the committed cursors, completed all 13 sources through transactional subsets, and discovered 15 genuinely unseen items without recreating previously seen candidates.
- JSON-list sources separate material item identity from a moving result window. Revision-only changes and reordering are observable but do not create duplicate candidates; genuinely unseen repository identities still do.
- Controlled tests distinguish exact duplicates, semantic/capability duplicates, updates, and genuinely new capabilities.
- All 110 real discoveries have explicit decisions: 103 were not promoted to independent Skills, 4 merged, 2 updated existing capability evidence, and 1 created a Skill. The review queue is zero; legacy `discard` records remain intact and are reported as `not_promoted` rather than deleted.
- The generated `github-release-evidence` Plugin contains one original `audit-github-release` Skill with source provenance, positive/negative trigger reviews, and a deterministic nine-gate end-to-end checker including optional immutable Release proof.
- Read-only `status` and `review-queue` commands expose durable handoff state without opening JSON files.
- A weekly/manual GitHub Actions workflow performs only deterministic scanning and opens a changed-only review PR. It never applies a semantic decision or publishes a Skill.
- Repository validation covers structure, state/catalog/decision consistency, generated artifact hashes, source references, and secret-like material. Release ZIPs are deterministic and are installed and invoked from an isolated temporary directory.
- The published v0.1.1 source archive installs and invokes successfully from a fresh download, and the released Plugin's own Skill returns `complete` against the live PR, CI, annotated tag, immutable Release, assets, installation, and contributor evidence.

GitHub API sources support either `GITHUB_TOKEN` from the current process or the official `gh` keyring via `--github-auth gh-cli`. Environment tokens are sent only to `api.github.com`, are not forwarded across redirects, and are never persisted or printed. The `gh-cli` path invokes `gh api` without exporting or placing a credential on the command line. The discovery search intentionally follows a moving `sort=updated` window, so an immediate repeat can truthfully discover new repository identities while revision-only churn is suppressed.

## Product boundary

- [RepoPilot Skillforge](https://github.com/KanadeK/repopilot-skillforge) scans one supplied codebase and writes repository-level guidance. This project watches public evidence over time and maintains a cross-source Skill catalog.
- Subscription mirrors and large Skill corpora distribute or retrieve existing bodies. This project does not republish upstream Skills; representative Skills are fingerprinted only for deduplication.
- Community directories and discussion are discovery signals, never authority for operational instructions.

The complete boundary and acceptance criteria are in [docs/spec.md](docs/spec.md); research and authority sources are in [docs/research.md](docs/research.md).

## Scale architecture

The long-term model has three layers:

- Evidence/Discovery retains high-volume source metadata, versions, license/trust facts, summaries, and fingerprints while raw bodies remain temporary.
- Capability Registry owns stable canonical capability IDs, one primary family, versioned facets, aliases, variants, merged evidence, decision history, and reactivation conditions.
- Published Skills contains only capabilities that pass the quality gates, packaged into small user-task Plugins or Collections rather than one enormous installation.

The active backend remains `git-json-v1`. Crossing a measured threshold opens a migration evaluation; it does not silently rewrite storage. See [architecture](docs/architecture.md), [taxonomy](docs/taxonomy.md), [schema migrations](docs/schema-migrations.md), [scale audit](docs/scale-audit.md), [roadmap](docs/roadmap.md), and the accepted [storage decision](docs/decisions/0001-defer-indexed-storage-until-measured-trigger.md).

## Quick start

Python 3.12 or newer is required. Runtime and tests use only the standard library.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --no-build-isolation -e .
.\.venv\Scripts\skill-harvester --help
```

Run a registered source subset:

```powershell
.\.venv\Scripts\skill-harvester scan --root . --source openai-build-skills
```

Run all registered sources, using `GITHUB_TOKEN` if the GitHub API needs authenticated rate limits:

```powershell
.\.venv\Scripts\skill-harvester scan --root .
```

Or reuse an existing official GitHub CLI login without exporting its keyring credential:

```powershell
.\.venv\Scripts\skill-harvester scan --root . --github-auth gh-cli
```

Inspect the durable handoff state and pending review queue:

```powershell
.\.venv\Scripts\skill-harvester status --root .
.\.venv\Scripts\skill-harvester review-queue --root .
.\.venv\Scripts\skill-harvester review-queue --root . --after CANDIDATE_ID
```

The review page size defaults to `review_batch.default` in `config/scale-policy.json`. An explicit `--limit <count>` must not exceed the policy's `review_batch.maximum`.

A scan stores only source metadata, necessary extracted facts, and evidence hashes. It does not store raw pages or execute fetched code. Review a discovery by creating the explicit decision contract documented in [.agents/skills/maintain-skill-harvester](.agents/skills/maintain-skill-harvester/SKILL.md), then apply it:

```powershell
.\.venv\Scripts\skill-harvester apply --root . --decision candidates/reviewed/CANDIDATE_ID.json
```

## Validate and package

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 scripts/run_evals.py
py -3.12 scripts/validate_repo.py
py -3.12 scripts/benchmark_storage.py --root . --records 100
py -3.12 scripts/build_release.py
py -3.12 scripts/verify_release_archive.py
```

CI runs the same gates on current Ubuntu and Windows runners. A separate weekly/manual workflow scans from the persisted cursor and opens a PR only when discoveries exist. The build creates:

- `codex-skill-harvester-v0.1.1.zip`
- `github-release-evidence-v0.1.1.zip`
- `SHA256SUMS.txt`

## Install the generated Plugin

Add this repository as a Codex marketplace source, pinned to the release tag:

```text
codex plugin marketplace add KanadeK/codex-skill-harvester --ref v0.1.1
```

Restart the ChatGPT desktop app, open the Plugins Directory in Codex or Work mode, choose **Codex Skill Harvester**, and install **GitHub Release Evidence**. This follows the [official repo-marketplace flow](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

## Repository map

- `sources/registry.json` — fixed source, trust, license, adapter, and optional authentication metadata.
- `state/harvest-state.json` — successful per-source cursor and seen-item state.
- `candidates/` and `decisions/` — discoveries, reviewed decisions, and append-only outcome records.
- `catalog/capabilities.json` and `catalog/taxonomy.json` — canonical capabilities, representative external fingerprints, and versioned classification.
- `config/scale-policy.json` — active backend, review budget, projection targets, and measured migration triggers.
- `plugins/` and `.agents/plugins/marketplace.json` — installable task-domain Plugin output.
- `evals/` — Codex-reviewed trigger cases and deterministic end-to-end fixtures.
- `runs/` — machine-readable and human-readable scan/delivery reports.

## License

MIT. Source facts retain their declared authority and license metadata; generated Skill prose and scripts are original synthesis.
