# Capability taxonomy

## Identity model

Every capability has:

- exactly one immutable canonical `id`;
- exactly one `primary_family`, expressed as an evidence-backed dotted path such as `software.release-assurance`;
- zero or more aliases;
- one or more values in every required facet;
- zero or more tool/platform variants;
- source evidence and merge/update history.

The current canonical id may resemble `plugin-id:skill-name`, but it is no longer derived from the packaging path after creation. Moving a Skill between Plugins must not change its id. Old names become aliases.

## Facets

The machine-readable vocabulary is `catalog/taxonomy.json`.

| Facet | Purpose | Examples |
| --- | --- | --- |
| `domain` | Broad task area | software, data, documents, research, design, media, operations, business, science, education, daily-life |
| `intent` | User action | discover, research, create, transform, analyze, diagnose, operate, validate, publish, maintain |
| `inputs` | Material accepted | file, webpage, repository, food, clothing, household context, shopping needs |
| `outputs` | Material produced by Codex | instructions, plan, decision, evidence, file, report, code, release |
| `tools` | Tools used by Codex or required for the guided task | gh, Python, Codex, household appliance, kitchen tools |
| `platforms` | Software platform or real execution environment | GitHub, Windows, Codex, fresh market, grocery store, home kitchen, laundry area |
| `side_effects` | Observable mutation by Codex or the guided human | read-only, local-write, human physical action, household consumption, external publish |
| `risk` | Elevated consequence | standard, allergen, food safety, physical safety, credentials, financial, medical, legal, high-risk |
| `volatility` | Recheck cadence | stable, periodic, fast-moving |
| `maturity` | Lifecycle | signal, candidate, verified, published, deprecated |
| `trust` | Evidence authority | official, primary, community, discovery |

Values are lower-case kebab-case in JSON. Extensible means a later taxonomy version may register a new value when evidence requires it; an unknown value is not accepted silently.

`platforms` has one meaning across the catalog: the environment in which the capability is carried out. For software work that may be GitHub or Windows; for a human-guided workflow it may be a fresh market, home kitchen, or laundry area. A physical environment is never relabeled as a software ecosystem. The seven-field fingerprint schema is unchanged because it already expresses this execution boundary honestly.

## Daily Life execution model

`daily-life` is a first-class domain. Its initial primary families are `daily-life.fresh-market-and-grocery-shopping`, `daily-life.laundry-and-clothing-care`, and `daily-life.home-cooking-and-meal-preparation`.

Codex asks, decides, sequences, checks, and helps recover; the user performs purchases, washing, cooking, and other physical actions. Skill output is therefore instructions, plans, observable signals, and decisions. A Skill must not claim the physical result already occurred. Broad concepts such as cooking are Plugin or capability-family boundaries, while a triggerable Skill owns one concrete user task.

## Classification rules

1. Start from the user's goal and behavior boundary, not the source website.
2. Select one primary family. Multiple domains belong in facets, not multiple primary families.
3. Keep the full capability fingerprint as the semantic comparison contract. Facets accelerate filtering but never replace it.
4. Treat the same capability on another tool as a variant or reference unless inputs, outputs, side effects, or user-visible behavior materially differ.
5. New official evidence normally updates or merges into the existing canonical id.
6. A merged capability records `merged_source_refs`; an old name records an alias; a retired capability records its successor.
7. A non-promoted candidate remains at maturity `candidate` or `signal` and records explicit reactivation conditions.

## Versioning

`taxonomy_version` uses semantic versioning:

- patch: wording or metadata clarification with no classification change;
- minor: additive facet values or optional dimensions;
- major: changed interpretation, cardinality, or canonical identity rules.

Catalog shape uses integer `schema_version`. A taxonomy change does not require rewriting every record unless its meaning changes. Deprecated values remain resolvable through aliases until an explicit migration removes them.
