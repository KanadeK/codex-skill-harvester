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
| `domain` | Broad task area | software, data, documents, research, design, media, operations, business, science, education, life |
| `intent` | User action | discover, research, create, transform, analyze, diagnose, operate, validate, publish, maintain |
| `inputs` | Material accepted | file, webpage, repository, spreadsheet, image, audio, API, report, code, release |
| `outputs` | Material produced | file, report, code, release, decision, evidence |
| `tools` | Required execution tools | gh, Python, Codex |
| `platforms` | Runtime/ecosystem boundary | GitHub, GitHub Actions, Windows, macOS, Linux, Codex |
| `side_effects` | Observable mutation | read-only, local-write, network-read, network-write, external-publish |
| `risk` | Elevated consequence | standard, credentials, financial, medical, legal, high-risk |
| `volatility` | Recheck cadence | stable, periodic, fast-moving |
| `maturity` | Lifecycle | signal, candidate, verified, published, deprecated |
| `trust` | Evidence authority | official, primary, community, discovery |

Values are lower-case kebab-case in JSON. Extensible means a later taxonomy version may register a new value when evidence requires it; an unknown value is not accepted silently.

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
