# Spec: Codex Skill Harvester v0.1.x

## Objective

Create a public, local-first OSS repository that incrementally discovers changed public material, extracts reviewable workflow facts, compares candidate capabilities against its own catalog and representative external skills, and publishes only useful, original, source-traceable Codex skills grouped into task-domain plugins.

The primary operator is a Codex maintainer working inside this repository. A later request such as "scan again" must resume from the last successful persisted source state without depending on chat memory.

### Product boundary

- This is not RepoPilot Skillforge. RepoPilot inspects one supplied code repository and generates repository-local onboarding/review/release guidance.
- This is not a skill subscription mirror such as skillx. The harvester does not clone and republish upstream skill bodies.
- This is not a large skill retrieval corpus such as SkillCorpus. The v0.1 product maintains a small reviewed catalog and synthesizes original workflows from authoritative material.

## Tech stack

- Python 3.12+
- Python standard library only at runtime and in tests
- JSON for source registry, state, discoveries, decisions, catalog, eval cases, and machine-readable run reports
- Markdown for human run reports and generated `SKILL.md` files
- GitHub Actions for Linux/Windows validation

Framework-specific behavior is limited to the documented Codex Skill/Plugin file formats. Their authority sources are listed in `docs/research.md`.

## Commands

- Scan configured sources: `python -m skill_harvester scan --root .`
- Scan with the current official GitHub CLI keyring login: `python -m skill_harvester scan --root . --github-auth gh-cli`
- Scan a subset: `python -m skill_harvester scan --root . --source <source-id>`
- Inspect durable repository state: `python -m skill_harvester status --root .`
- List a bounded pending review page: `python -m skill_harvester review-queue --root . --limit 100 [--after <candidate-id>]`
- Apply one reviewed candidate decision: `python -m skill_harvester apply --root . --decision candidates/reviewed/<id>.json`
- Validate repository and generated artifacts: `python scripts/validate_repo.py`
- Run tests: `python -m unittest discover -s tests -v`
- Build deterministic release archives: `python scripts/build_release.py`

## Project structure

- `src/skill_harvester/`: deterministic CLI, source adapters, state, dedupe recommendations, decision application, and validation
- `sources/registry.json`: fixed source registry with authority, trust, license, and adapter metadata
- `state/harvest-state.json`: last successful cursors and seen evidence
- `catalog/capabilities.json`: published capabilities and full fingerprints
- `candidates/inbox/`: changed-source discoveries awaiting Codex review
- `candidates/reviewed/`: explicit reviewed decisions ready to apply
- `decisions/`: append-only applied and rejected decision records
- `plugins/`: installable task-domain plugins and their generated skills
- `.agents/skills/`: repository-scoped maintainer workflow
- `evals/`: positive trigger, negative trigger, and end-to-end cases
- `runs/`: committed machine and human reports for real scans
- `tests/fixtures/`: controlled source and decision examples; no external executable content
- `scripts/`: repository validation and deterministic release packaging
- `tasks/`: durable implementation plan and checklist

Directories are created only when their first real file is added.

## Code style

Use explicit immutable records and pure transformations where possible:

```python
@dataclass(frozen=True)
class CapabilityFingerprint:
    goal: str
    triggers: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    tools: tuple[str, ...]
    side_effects: tuple[str, ...]
    platforms: tuple[str, ...]
```

Keep network I/O at the source boundary, pass fetched bytes into pure extractors, and use temporary files only for raw bodies. Do not introduce a helper or abstraction for a single call site.

## Data and decision contracts

### Source state

Each source records its adapter, trust tier, authority role, license status, ETag/Last-Modified when available, logical cursor, content hash, seen entry IDs, and last successful observation time. A scan stages all selected source updates in memory and atomically commits them only if every selected source succeeds.

### Capability fingerprint

Every candidate and catalog entry covers at least:

- `goal`
- `triggers`
- `inputs`
- `outputs`
- `tools`
- `side_effects`
- `platforms`

### Decision ownership

The program may deterministically recommend:

- `discard_exact`: identical canonical bundle hash
- `merge_semantic`: materially the same capability fingerprint
- `update_existing`: an identified capability has new authoritative evidence or behavior
- `create_new`: no catalog capability covers the task

Only a reviewed decision marked `reviewed_by: codex` may merge, update, or create a published skill. The rationale must name the compared capability IDs and source evidence. Exact byte duplicates may be rejected automatically and are still reported.

## Source and content safety

- Only `https://` network sources are accepted.
- Network responses have bounded size and timeout.
- GitHub API authentication may use a process-scoped `GITHUB_TOKEN` or `gh api`; credentials are never persisted, printed, or placed in command arguments.
- Redirects must remain HTTPS.
- Raw bodies live only in an OS temporary directory during a run.
- Extracted instruction-like text is stored as quoted evidence/facts and never executed.
- Downloaded scripts are never invoked.
- Unknown or incompatible license status blocks copying; synthesis may use necessary factual observations with attribution.
- Generated skills must be original writing and include source URLs and observed revisions in a concise reference file when details are conditional.

## Testing strategy

- Unit tests: normalization, fingerprints, exact hash dedupe, semantic recommendation, update recommendation, JSON validation, and path safety.
- Integration tests: fake in-memory fetcher exercises transactional scans and cursor persistence.
- Incremental proof: the same fixture source is scanned twice; the second run reports a no-op and creates no duplicate discovery.
- Fixture decisions: distinguish exact duplicate, semantic duplicate, update, and new capability.
- Skill evals: positive triggers, negative non-triggers, format validation, and one end-to-end task artifact.
- Isolated script proof: copy the repository to a temporary directory and run the CLI/validator there.
- Live proof: scan at least one real official source, apply at least one original reviewed skill, then run a second unchanged scan that reports no-op.

## Boundaries

- Always: preserve provenance, record rejections, validate all generated skills/plugins, and keep cursor writes transactional.
- Ask first: runtime dependencies, hosted services, embeddings/API costs, a new product identity, or publication with a red gate.
- Never: execute fetched code, persist raw pages, expose credentials, copy unknown-license skills, synthesize unverifiable procedures, or publish a source summary as a skill.

## Success criteria

- The target is an independent nested Git repository; the outer workspace and sibling repositories remain untouched.
- Name and overlap research is recorded, including the distinction from RepoPilot Skillforge, skillx, and SkillCorpus.
- A real source registry includes current official OpenAI Skill/Plugin authority, vendor official docs/examples, GitHub incremental discovery, a public API/registry, and release/changelog/RSS sources.
- Two consecutive runs of the same pipeline demonstrate changed-only processing; an unchanged second run is a truthful no-op.
- Controlled fixtures prove exact duplicate, semantic duplicate, update, and genuinely new outcomes.
- At least one useful original skill is generated or updated from a real official source and is traceable to evidence.
- Skill and Plugin format validation, positive/negative trigger evals, an end-to-end task, and isolated execution pass.
- CI validates repository structure, state consistency, generated Skill/Plugin format, tests, and release build on pull requests and `main`.
- No external script is executed; no secret, private data, unauthorized material, or substantial copied text is committed.
- The run report lists discoveries, rejections, merges, updates, creations, sources, validation, and unresolved issues.
- The public GitHub repository, merged PR, green remote CI, annotated tag, Release assets, install/call path, author history, and GitHub contributors are verified before v0.1.0 is declared complete.

## Open questions

None that block v0.1.x. Hosted semantic embeddings, unattended semantic publication, and a large multi-plugin catalog remain explicit non-goals.

## v0.1.1 maintenance scope

- Review every candidate carried over from v0.1.0 and persist a concrete Codex decision; source listings and release titles are rejected when they do not contain enough authoritative workflow evidence.
- Treat the moving GitHub repository-search window separately from material item changes. Revision-only churn and reordering must not create discoveries, while new identities or changed titles/URLs must.
- Add read-only `status` and `review-queue` commands for durable operator handoff.
- Add a scheduled/manual GitHub workflow that performs deterministic scans and opens a pull request only when discoveries exist. It must never apply semantic decisions or publish Skills.
- Add repository security/community metadata, dependency update configuration, and remote default-branch protection without adding runtime dependencies.
- Update the existing release-audit Skill only when reviewed authoritative evidence changes a useful gate; validate its format, triggers, and isolated end-to-end behavior before release.
- Publish changes as immutable v0.1.1 after local gates, pull-request CI, remote settings, release assets, source installation, Skill invocation, and contributors are verified.

## Scale architecture foundation scope

### Objective

Prepare the harvester to evolve toward millions of source observations, hundreds of thousands of discoveries, tens of thousands of normalized capability candidates, and thousands of published Skills without treating those numbers as publication targets. Preserve the existing quality gates and implement only the foundations that are required before another broad scan.

### Assumptions and decisions

- The current Git-native JSON layout remains the active backend until a measured migration trigger is crossed. This change does not introduce SQLite, Parquet, embeddings, hosted services, or a runtime dependency.
- Legacy decision outcome `discard` means `not_promoted`: the evidence and decision stay durable and may be reconsidered. New operator output must not imply deletion.
- A capability has one immutable canonical `id`. Its Plugin, Skill path, aliases, facets, evidence, and variants may evolve without changing that identity.
- Classification uses one primary capability family plus versioned multi-dimensional facets. Taxonomy values may grow from evidence; the initial registry is not an exhaustive ontology.
- Source fetching, semantic review, and publication remain separate stages. A metric is emitted only by the stage that actually measured it; unperformed semantic work is never reported as zero.

### Required behavior in this change

- Document the three-layer architecture: Evidence/Discovery, Capability Registry, and Published Skills.
- Add a validated, versioned taxonomy contract covering domain, intent, inputs, outputs, tools, platforms, side effects, risk, volatility, maturity, and trust.
- Add an explicit schema/taxonomy migration policy and prove legacy catalog migration with deterministic fixtures.
- Normalize legacy `discard` counts to `not_promoted` in operator-facing status while retaining old append-only records unchanged.
- Require explicit reactivation conditions for new schema-version-2 `not_promoted` decisions.
- Bound review queue pages with a stable continuation cursor and deterministic trust-based priority.
- Add discovery-stage metrics for selected/succeeded/failed sources, staged discoveries, newly enqueued candidates, and exact record duplicates.
- Add a reproducible storage inventory/benchmark and explicit thresholds that decide when the Git-JSON backend must be replaced or indexed.
- Update repository validation and CI so these contracts cannot silently drift.

### Success criteria

- Existing 110 candidates and 110 decision records remain valid and byte-preserved unless a file is directly required by the new catalog contract.
- Status reports 103 legacy `discard` records as 103 `not_promoted` decisions and reports zero deleted records.
- A schema-version-2 `not_promoted` decision without reactivation conditions fails; one with conditions is accepted and remains unpublished.
- Review queue output defaults to a bounded batch, exposes priority and a continuation cursor, and can resume without duplicating an item.
- Scan fixtures distinguish staged discoveries, new queue entries, and exact queue-record duplicates; failed transactional runs report the measured source failure without advancing state.
- The scale benchmark inventories the current backend, exercises temporary synthetic records, projects the named target sizes, and evaluates migration triggers without writing benchmark data into the repository.
- The complete unit/integration suite, repository validator, evals, release build, isolated archive verification, and Linux/Windows CI remain green.
- Work is submitted on a `codex/` branch in one reviewable PR. This change is not merged, tagged, or released automatically.

### Non-goals

- No broad source scan or candidate-generation campaign.
- No automatic semantic approval or Skill publication.
- No storage backend rewrite before a measured trigger.
- No attempt to enumerate every possible domain or publish thousands of Skills into one Plugin.

### Open questions for later control-plane decisions

- Which model-usage and cost telemetry is authoritative enough to populate per-candidate token and currency metrics without estimates being mistaken for measurements?
- When a storage trigger is crossed, should the first indexed backend optimize for a single maintainer (SQLite) or coordinated workers (a service-backed queue)? The current local-first default is SQLite unless operational evidence changes the requirement.
