# Engineering status

This is the maintainer-facing handoff for 会过日子 · Human Skills. The public product surface lives in [README.md](../README.md), [README.en.md](../README.en.md), and [SKILLS.md](../SKILLS.md).

## Release state

- Candidate version: v0.2.0
- Public stable version before this release workflow completes: [v0.1.1](https://github.com/KanadeK/codex-skill-harvester/releases/tag/v0.1.1)
- Candidate inventory: 17 Skills in 11 Plugins
- Daily Life acceptance bank: 63 resolved scenarios, 21 in each of three task families
- Runtime authority: SQLite v4
- Release is not complete until the final main CI, annotated tag, GitHub Release assets, checksums, isolated download/install/invocation, repository metadata, and remote readback all pass.

## Measured campaign state

The completed 2026-08-30 capacity campaign met its explicit lower-bound objective without using Skill output as a quota:

- 204 revision-pinned executable endpoints
- 1,622 unique actual queries completed in 1,626 attempts
- 4 recoverable query failures and 151 discovery hits
- 204 successful source requests in the final ramp
- 517,498 bytes downloaded and 116 changed observations inserted in that ramp
- 58 Evidence Packs, 26 normalized candidates, and 263 bounded L3 recalls across eight resumable semantic batches
- 26 supervised L4 decisions: 15 not_promoted, 1 merge, 3 updates, and 7 creates
- Usage credits and semantic-review tokens remain measured=false because there was no authoritative meter

The follow-on Daily Life pilot added:

- 20 actual bilingual queries, 18 unique reviewed hits, 13 selected executable sources, and 5 authority endpoints retained as not_selected because they returned HTTP 403
- 13 observations, 12 Evidence Packs, 9 normalized candidates, and 156 L3 recalls
- 9 supervised creates plus 3 evidence-level safety non-promotions
- 9 instruction-only Skills in 3 task-domain Plugins
- 63 resolved plan/live/recovery scenarios: 9 create, 45 merge, 9 not_promoted, 0 pending
- Query, semantic, and one stable official source replayed as no-op

After both slices, repository validation reports 217 source states, 1,217 observations, 180 Evidence Packs, 145 candidates and decisions, 17 Skills, and 11 Plugins. These are measured outcomes, not publication KPIs.

Authoritative compact reports:

- [Full content-production campaign](../runs/2026-08-30-full-content-production.json)
- [Daily Life pilot](../runs/2026-08-31-daily-life-pilot.json)
- [First production slice](../runs/2026-08-29-content-production.json)
- [v0.1.1 final attestation](../runs/2026-08-27T14-31-10Z-v0.1.1-attestation.md)

## Authority and lifecycle

The repository has three deliberately separate layers:

1. Evidence/Discovery stores source identity, revision, trust, license, compact facts, hashes, observations, and cursors. Raw pages remain temporary.
2. Capability Registry stores one canonical capability ID, seven-field fingerprint, facets, aliases, variants, merges, updates, decisions, and reactivation conditions.
3. Published Skills stores only original, trigger-safe, installable, E2E-verified artifacts grouped into small user-task Plugins.

Runtime observation, Evidence Pack, candidate, query/semantic batch, five-queue, decision, and checkpoint state has one authority: [state/runtime.db](../state/runtime.db), schema 4. There is no legacy JSON runtime fallback or dual write. Git remains authoritative for Skills, manifests, catalog snapshots, evals, compact reports, and release history.

The migration contract is documented in [ADR-002](decisions/0002-adopt-sqlite-runtime-store.md) and [schema-migrations.md](schema-migrations.md). Current data flow and responsibility boundaries are in [architecture.md](architecture.md), [spec.md](spec.md), and [plan-adoption-audit.md](plan-adoption-audit.md).

## Quality and safety gates

Each promoted capability must have:

- a distinct reusable user goal and complete goal/triggers/inputs/outputs/tools/side_effects/platforms fingerprint;
- traceable high-trust evidence and a supervised L4 not_promoted/merge/update/variant/create decision;
- original synthesis rather than copied upstream instructions;
- positive-trigger and negative-misfire evaluation;
- an end-to-end task, isolated install/invocation proof, license check, and deterministic script test when a script exists;
- an explicit safety boundary and no automatic publication for medical, legal, financial, credential-heavy, high-privilege, or real-world-control work.

External pages are untrusted data. The harvester does not execute downloaded third-party scripts and does not commit unknown-license page bodies.

## Local verification

Use Python 3.12 or later from the repository root.

    python -m unittest discover -s tests
    python -m skill_harvester.cli run-evals --repo .
    python -m skill_harvester.cli validate --repo .
    python -m skill_harvester.cli benchmark --repo .
    python -m skill_harvester.cli build-release --repo . --output <temporary-directory>
    git diff --check

Release validation additionally runs the official bundled Skill validator over all 17 Skill directories, the official bundled Plugin validator over all 11 Plugin directories, two independent deterministic builds, isolated installation and invocation from every archive, secret/originality checks, and Ubuntu/Windows CI.

## Historical context

- v0.1.0 proved one real source-to-Skill vertical slice.
- v0.1.1 repaired moving GitHub search-window identity, reviewed the entire legacy queue, added review-only automation, and published immutable verified artifacts.
- PR #7 landed the scale/storage foundation. PR #9 accumulated the full campaign and Daily Life pilot but diverged after the squash merge; this release branch reproduces its exact resulting tree on current main before applying public brand and release changes. The release PR records the supersession evidence.

Predicted scale ranges remain planning inputs, never promises or reasons to manufacture candidates. A no-op means the supplied stable inputs have no new, changed, or unfinished work; it does not permanently end future campaigns.
