# Codex Skill Harvester

[简体中文](README.md)

[![CI](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/codex-skill-harvester/actions/workflows/ci.yml)

Codex Skill Harvester is the **background discovery, evidence, deduplication, and maintenance engine** for public workflows. It incrementally reads trusted sources, turns raw discoveries into Evidence Packs and normalized capabilities, applies supervised semantic adjudication, and maintains verifiable Codex / Open Agent Skills.

> Looking for everyday Skills written for people to read and “install”? Go to:
>
> **[Skills for Humans](https://github.com/KanadeK/skills-for-humans) / 给人类的 Skill**.

The repositories have different jobs:

- **Skill Harvester** owns sources, cursors, evidence, capability fingerprints, deduplication, candidates, decisions, validation, and release engineering.
- **Skills for Humans** contains final SKILL.md files read and executed directly by people, without the database, campaigns, or candidate queue.

## Where v0.2.0 belongs

[v0.2.0](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.2.0) remains an immutable historical technical prototype. It proved 204 executable endpoints, 1,622 real queries, SQLite v4, content review, 17 Skills, 11 Plugins, cross-platform CI, and immutable Release engineering. Its everyday-life Plugins were mistakenly presented as this repository's frontstage product.

That public history will not be deleted or rewritten. The corrected split is:

    codex-skill-harvester
        discover → evidence → deduplicate → supervise → validate → maintain
                                             |
                                             └── qualified human content goes to skills-for-humans

The v0.2.0 Skills, Plugins, evals, and reports remain here as a technical prototype, regression corpus, and maintenance evidence. They no longer define the Harvester's public brand.

## What the engine does

### 1. Evidence / Discovery

- A fixed source registry covers official documentation, CLI/API/OpenAPI, primary repositories, Releases/Changelogs, RSS/Atom, sitemaps, and bounded discovery queries.
- Sources retain trust, license, revision, ETag/Last-Modified, query, and cursor state.
- External content is always untrusted data. Raw pages stay in temporary cache, downloaded third-party scripts are never executed, and unknown-license bodies are not committed.

### 2. Capability Registry

- An observation enters content review before it can become an Evidence Pack and normalized candidate.
- Capability fingerprints cover goal, triggers, inputs, outputs, tools, side_effects, and platforms.
- Exact hashes handle copies. L2/L3 provide recall only; supervised L4 decides not_promoted, merge, update, variant, or create.
- not_promoted retains source, reason, and reactivation conditions instead of deleting evidence.

### 3. Published artifacts

- Publication candidates require a distinct user goal, trusted evidence, original synthesis, clear trigger boundaries, format, E2E, installation, and license gates.
- Git owns Skills/Plugins, catalogs, evals, compact reports, and release history.
- Human-readable everyday content now ships through [Skills for Humans](https://github.com/KanadeK/skills-for-humans).

## Sole runtime authority

Runtime observations, Evidence Packs, candidates, query/semantic batches, five queues, decisions, source cursors, and checkpoints have one authority: [state/harvest.sqlite3](state/harvest.sqlite3), SQLite schema 4.

There is no Git-JSON fallback, long-lived dual write, or second source of truth. Future migrations retain the write-validate-atomic-swap contract and state the old-path deletion condition.

## Local use

Requires Python 3.12+.

    python -m venv .venv
    .\.venv\Scripts\python -m pip install --no-build-isolation -e .
    .\.venv\Scripts\skill-harvester status --root . --json
    .\.venv\Scripts\skill-harvester review-queue --root . --json

Maintenance and verification:

    .\.venv\Scripts\python -m unittest discover -s tests -v
    .\.venv\Scripts\python scripts/run_evals.py
    .\.venv\Scripts\python scripts/validate_repo.py
    .\.venv\Scripts\python scripts/benchmark_storage.py
    .\.venv\Scripts\python scripts/build_release.py

Scheduled GitHub Actions runs a bounded campaign and opens a review PR. It never performs unattended L4 merges, publishes a Skill, or creates a Release.

## Current durable state

- 217 registered sources and source states
- 1,217 observations
- 180 Evidence Packs
- 145 adjudicated candidates
- 1,642 Topic Bank queries
- SQLite v4 with zero pending candidates

Scale numbers are measured outcomes, not Skill-production KPIs. See [Engineering Status](docs/engineering-status.md) for campaign metrics, migrations, and verification evidence.

## Safety and scope

- Never execute downloaded third-party scripts, store secrets, or treat community discussion as operational authority.
- Medical, legal, financial, credential-heavy, high-privilege, and real-world-control capabilities remain evidence-only and blocked from automatic publication.
- An empty queue is not permanent campaign completion. A no-op only describes the same input set with no new, changed, or unfinished work.
- [RepoPilot Skillforge](https://github.com/KanadeK/repopilot-skillforge) analyzes one supplied repository and writes repository-local guidance. Harvester maintains a cross-source capability ecosystem.

## Documentation

- [Specification](docs/spec.md)
- [Architecture](docs/architecture.md)
- [Plan Adoption Audit](docs/plan-adoption-audit.md)
- [Taxonomy](docs/taxonomy.md)
- [Schema migrations](docs/schema-migrations.md)
- [Engineering Status](docs/engineering-status.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

Skill-format claims rely only on OpenAI's official [Skills documentation](https://developers.openai.com/codex/skills). External sources supply facts and discovery signals only.

## License

[MIT](LICENSE)
