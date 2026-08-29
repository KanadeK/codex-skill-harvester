# Scale architecture

## Product scale is not a publication target

The harvester may evolve toward millions of source observations, hundreds of thousands of discoveries, tens of thousands of normalized capability candidates, and thousands of published Skills. Those figures are capacity envelopes. A high non-promotion rate is expected because publication still requires authoritative evidence, a repeatable task, a distinct user goal, clear inputs and outputs, and verifiable behavior.

Users install small task-domain Plugins or Collections. They do not install the evidence corpus or the complete capability registry.

## Three product layers

| Layer | Owns | Does not own | Current implementation | Scale target |
| --- | --- | --- | --- | --- |
| Evidence/Discovery | Source identity, cursor, revision, trust, license, necessary facts, evidence hash, exact dedupe | Semantic approval, copied third-party bodies, published instructions | `sources/registry.json`, `state/harvest.sqlite3`, temporary raw responses | Partitioned evidence metadata with per-source cursors; indexed storage only after a measured need |
| Capability Registry | Canonical id, fingerprint, family, facets, aliases, variants, merge/update history, non-promotion rationale and reactivation conditions | Plugin installation layout as identity, raw pages | Git catalog plus SQLite runtime decision/queue records | Indexed queue and immutable decision log with a rebuildable semantic index |
| Published Skills | Original validated Skill bodies, scripts, evals, Plugin/Collection manifests | Discovery noise or every candidate | `plugins/`, `.agents/plugins/marketplace.json`, `evals/` | Curated, task-domain Plugins containing a bounded set of coherent Skills |

## Data flow

```text
registered sources
      |
      v
bounded fetch -> temporary raw body -> normalized evidence metadata
      |                                      |
      | exact hash / source cursor           v
      +------------------------------> discovery queue
                                             |
                                      budgeted Codex review
                                             |
                    +------------------------+----------------------+
                    |                        |                      |
               not promoted             merge/update             create
                    |                        |                      |
          durable reason and          canonical capability registry
          reactivation condition                 |
                                                 v
                                      validated published Skill
                                                 |
                                                 v
                                      small task-domain Plugin
```

Deterministic code owns fetching, exact hashes, cursors, persistence, schema validation, queue boundaries, and measured metrics. Codex owns semantic comparison, family/facet judgment, near-duplicate decisions, synthesis, and promotion. A derived embedding or search index may accelerate comparison later, but it is never authoritative.

## Invariants

- External content is untrusted data. Raw bodies remain temporary and downloaded scripts are never executed.
- A successful selected scan commits all selected source cursors and queue records atomically; a failed selection advances none.
- Every capability has one immutable canonical `id`. Plugin id, Skill directory, display name, aliases, facets, and variants may change without rewriting that id.
- Exact byte equality is only duplicate detection. Capability equivalence uses the full fingerprint and reviewed evidence.
- `not_promoted` is a reversible registry decision, not deletion. Provenance, rationale, and a reactivation condition remain queryable.
- Metrics belong to stages. Discovery does not claim zero merges when semantic review did not run.
- Schema and taxonomy versions are explicit. Unknown future schema versions fail fast.

## Incremental, sharded, and recoverable execution

The current backend is intentionally local-first and single-writer. Each source has its own logical cursor, each discovery and decision has a stable id, and each run is independently reportable. Selection by source already provides a transactional shard.

Bounded review pages prevent one round from attempting the complete queue. High-trust sources are checked every scheduled cycle; discovery queries rotate by topic once there is more than one discovery query. Each rotation owns its cursor and next-due time.

After a measured need beyond the SQLite envelope:

- Parquet may hold cold evidence metadata partitioned by source and observation month when analytical scans justify it.
- Git continues to hold schemas, source definitions, taxonomy, summaries, published Skills, evals, and migration manifests.
- Any semantic/vector index is derived and can be rebuilt without losing authority.

The migration changes the backend, not canonical capability ids or published Plugin contracts.

## Plugin and Collection boundaries

A Plugin groups Skills by a user task domain and coherent installation need. Sources never determine Plugin boundaries. A capability may have tool/platform variants while remaining one canonical capability. A new Skill is justified only when the user goal or behavior boundary is materially different.

When the published catalog grows, discovery and installation use a searchable catalog plus curated Collections. The repository never presents thousands of Skills as one installation unit.
