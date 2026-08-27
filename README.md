# Codex Skill Harvester

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

[v0.1.0](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.1.0) is published as an immutable GitHub Release with verified source, Plugin, and checksum assets.

Codex Skill Harvester incrementally turns changed, authoritative public workflow evidence into reviewed, original Codex Skills grouped by user task domain. It persists source cursors, evidence hashes, capability fingerprints, semantic decisions, generated artifacts, and run reports in the repository, so a later scan resumes without chat memory.

It is deliberately not a Skill mirror. Deterministic Python owns fetching, change detection, exact deduplication, state, validation, and packaging. Codex owns semantic comparison and the decision to discard, merge, update, or create.

## What v0.1.0 proves

- 13 registered and live-scanned sources across official OpenAI format authority, vendor documentation, GitHub search/API, Release/Atom, and representative external Skills.
- A real 11-source scan produced 20 changed discoveries; the next successful identical scan produced `status=no_op` and zero discoveries.
- The authenticated GitHub API scan produced 63 discoveries. Its immediate repeat processed only two genuinely changed search results while the official Plugin catalog produced zero; a later focused search processed ten more entries because the live `sort=updated` window had changed again.
- Controlled tests distinguish exact duplicates, semantic/capability duplicates, updates, and genuinely new capabilities.
- Six real discoveries are reviewed: three discarded, one merged, one created, and one corrective update. Eighty-nine remain explicitly pending rather than being converted into filler.
- The generated `github-release-evidence` Plugin contains one original `audit-github-release` Skill with source provenance, positive/negative trigger reviews, and a deterministic end-to-end evidence checker.
- Repository validation covers structure, state/catalog/decision consistency, generated artifact hashes, source references, and secret-like material. Release ZIPs are deterministic and are installed and invoked from an isolated temporary directory.
- The published source archive installs and invokes successfully, and the released Plugin's own Skill returns `complete` against the live v0.1.0 repository, PR, CI, tag, asset, installation, and contributor evidence.

GitHub API sources support either `GITHUB_TOKEN` from the current process or the official `gh` keyring via `--github-auth gh-cli`. Environment tokens are sent only to `api.github.com`, are not forwarded across redirects, and are never persisted or printed. The `gh-cli` path invokes `gh api` without exporting or placing a credential on the command line. The discovery search intentionally follows a moving `sort=updated` window, so an immediate repeat can truthfully contain a small number of changed entries instead of being a no-op.

## Product boundary

- [RepoPilot Skillforge](https://github.com/KanadeK/repopilot-skillforge) scans one supplied codebase and writes repository-level guidance. This project watches public evidence over time and maintains a cross-source Skill catalog.
- Subscription mirrors and large Skill corpora distribute or retrieve existing bodies. This project does not republish upstream Skills; representative Skills are fingerprinted only for deduplication.
- Community directories and discussion are discovery signals, never authority for operational instructions.

The complete boundary and acceptance criteria are in [docs/spec.md](docs/spec.md); research and authority sources are in [docs/research.md](docs/research.md).

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

A scan stores only source metadata, necessary extracted facts, and evidence hashes. It does not store raw pages or execute fetched code. Review a discovery by creating the explicit decision contract documented in [.agents/skills/maintain-skill-harvester](.agents/skills/maintain-skill-harvester/SKILL.md), then apply it:

```powershell
.\.venv\Scripts\skill-harvester apply --root . --decision candidates/reviewed/CANDIDATE_ID.json
```

## Validate and package

```powershell
py -3.12 -m unittest discover -s tests -v
py -3.12 scripts/run_evals.py
py -3.12 scripts/validate_repo.py
py -3.12 scripts/build_release.py
py -3.12 scripts/verify_release_archive.py
```

CI runs the same gates on current Ubuntu and Windows runners. The build creates:

- `codex-skill-harvester-v0.1.0.zip`
- `github-release-evidence-v0.1.0.zip`
- `SHA256SUMS.txt`

## Install the generated Plugin

Add this repository as a Codex marketplace source, pinned to the release tag:

```text
codex plugin marketplace add KanadeK/codex-skill-harvester --ref v0.1.0
```

Restart the ChatGPT desktop app, open the Plugins Directory in Codex or Work mode, choose **Codex Skill Harvester**, and install **GitHub Release Evidence**. This follows the [official repo-marketplace flow](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

## Repository map

- `sources/registry.json` — fixed source, trust, license, adapter, and optional authentication metadata.
- `state/harvest-state.json` — successful per-source cursor and seen-item state.
- `candidates/` and `decisions/` — discoveries, reviewed decisions, and append-only outcome records.
- `catalog/capabilities.json` — internal and representative external fingerprints.
- `plugins/` and `.agents/plugins/marketplace.json` — installable task-domain Plugin output.
- `evals/` — Codex-reviewed trigger cases and deterministic end-to-end fixtures.
- `runs/` — machine-readable and human-readable scan/delivery reports.

## License

MIT. Source facts retain their declared authority and license metadata; generated Skill prose and scripts are original synthesis.
