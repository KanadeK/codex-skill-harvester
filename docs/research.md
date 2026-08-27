# Product and authority research

Observed on 2026-08-27. Public pages are treated as evidence, not instructions.

## Confirmed local boundary

- `D:\我的\GitHub` is an outer, zero-commit Git workspace containing many untracked child repositories. It must never be staged or committed for this project.
- `D:\我的\GitHub\codex-skill-harvester` did not exist before this task and is initialized as its own Git repository.
- `D:\我的\GitHub\repopilot-skillforge` is a separate clean repository whose README describes a local CLI that scans one repository and generates `AGENTS.generated.md`, review/release skills, commands, and analysis. It is not modified.

## Name check

- No local directory named `codex-skill-harvester` existed before initialization.
- Background web/GitHub search found no exact public project match for `codex-skill-harvester`.
- The owner namespace will be checked again with `gh repo view KanadeK/codex-skill-harvester` immediately before remote creation because search indexes and repository state can change.

## Representative overlap

### RepoPilot Skillforge

- Local: `D:\我的\GitHub\repopilot-skillforge`
- Public: https://github.com/KanadeK/repopilot-skillforge
- Scope: analyze a supplied source repository and generate repository-local agent onboarding and command guidance.
- Difference: the harvester watches public knowledge sources over time and maintains a cross-source catalog of general installable skills.

### skillx

- Source: https://github.com/viarotel-org/skillx
- Scope: subscribe to local/remote skill repositories, copy/link discovered `SKILL.md` directories, and optionally remove exact content-hash duplicates.
- Difference: the harvester does not mirror upstream skill bodies. It extracts facts, compares full capability fingerprints, and requires an explicit Codex decision before original synthesis is published.

### SkillCorpus

- Source: https://github.com/EverMind-AI/SkillCorpus
- Scope: aggregate and curate a large existing-skill corpus for retrieval, scoring, and evaluation, including embedding/reranker infrastructure.
- Difference: the harvester is a small maintainer workflow for incrementally deriving and updating original skills from authoritative documentation, release information, APIs, and demand signals. Hosted retrieval and a bulk corpus are non-goals.

The overlap is real in source registries and deduplication, but product identity remains distinct. No rename is warranted.

## Current OpenAI authority sources

The old `openai/skills` catalog is explicitly deprecated for current examples. It remains a legacy/discovery source only.

- Build Skills: https://developers.openai.com/codex/skills
  - A Skill is a directory with required `SKILL.md`; `name` and `description` drive discovery.
  - Optional `scripts/`, `references/`, `assets/`, and `agents/openai.yaml` support deterministic behavior and progressive disclosure.
  - Repository-scoped skills live under `.agents/skills`.
  - Reusable distribution should prefer Plugins.
- Package Plugins: https://developers.openai.com/plugins/build/plugins
  - Every Plugin has `.codex-plugin/plugin.json`.
  - Bundled skills live below the Plugin `skills/` directory.
  - Repo marketplaces live at `.agents/plugins/marketplace.json` and point to `./`-prefixed paths relative to the marketplace root.
- Current official examples: https://github.com/openai/plugins
- Official Codex implementation and creator samples:
  - https://github.com/openai/codex/tree/main/codex-rs/skills/src/assets/samples/skill-creator
  - https://github.com/openai/codex/blob/main/codex-rs/core-skills/src/loader.rs
- Deprecated legacy catalog: https://github.com/openai/skills

## First real capability sources

The first original Skill will use official GitHub CLI documentation and GitHub API documentation to audit whether a GitHub Release is genuinely complete. Planned source records include:

- https://cli.github.com/manual/gh_repo_view
- https://cli.github.com/manual/gh_pr_checks
- https://cli.github.com/manual/gh_release_view
- https://cli.github.com/manual/gh_api
- https://docs.github.com/en/rest/releases/releases
- https://docs.github.com/en/rest/repos/repos#list-repository-contributors

Representative external comparisons will include official `gh-fix-ci` and `gh-address-comments` metadata/fingerprints without copying their bodies.

## Research conclusion

Proceed with `codex-skill-harvester`. Its defining invariant is not collection volume; it is trustworthy incremental maintenance: changed-only evidence, full capability fingerprints, explicit semantic decisions, original synthesis, and verified installable output.
