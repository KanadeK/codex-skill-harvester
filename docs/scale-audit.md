# Scale adaptation audit

Inventory measured on 2026-08-27 against v0.1.1 before the scale foundation. The temporary lifecycle benchmark was run on 2026-08-28 in the local Windows workspace with the bundled Python 3.12 runtime.

## Current inventory

| Data | Files | Bytes | Observation |
| --- | ---: | ---: | --- |
| Source registry | 1 | 4,555 | Small and bounded by configured connectors |
| Harvest state | 1 | 21,772 | Contains 100 `seen_items` and 24 `material_items`; rewritten atomically as one document |
| Candidate inbox | 110 | 108,498 | Average 986.3 bytes per candidate |
| Reviewed decisions | 110 | 161,532 | Average 1,468.5 bytes per candidate |
| Applied decision records | 110 | 143,077 | Average 1,300.7 bytes per candidate |
| Run reports | 43 | 54,562 | Small append-only history |

A completed candidate currently occupies about 3,755.5 bytes across three JSON files before Git object/index overhead. This is audit-friendly at the current size.

## Code-path findings

- Scan state deep-copies and rewrites the complete `harvest-state.json` after every successful selection.
- `seen_items` and `material_items` grow without compaction for list/feed sources.
- Status, queue, and repository validation enumerate and parse all candidate/decision files.
- Candidate and decision records are independently addressable and recoverable, but three files per lifecycle make filesystem and Git metadata the first likely constraint.
- Source selection is transactional and incremental; it already scales by connector/source shard.
- Review had no default budget or continuation cursor, so a large pending queue could be presented as one unit.
- Scan reports used decision-stage zeros even though no semantic review ran, making observability ambiguous.

## Payload projections

| Candidates | Lifecycle JSON files | Payload estimate |
| ---: | ---: | ---: |
| 10,000 | 30,000 | about 37.6 MB |
| 50,000 | 150,000 | about 187.8 MB |
| 100,000 | 300,000 | about 375.6 MB |
| 1,000,000 | 3,000,000 | about 3.76 GB |

Filesystem traversal, Git metadata, antivirus scanning, checkout, and CI time become material before raw bytes do.

The state sample uses about 21.8 KB for 100 seen entries plus fixed metadata. Linear extrapolation is deliberately conservative: 100,000 source items can make a tens-of-megabytes single rewrite, while one million can make it hundreds of megabytes.

## Historical decision (superseded)

Keep Git-JSON now. It is transparent, dependency-free, transactional at current volume, and below every migration trigger. Add bounded review and measurement first.

Open a storage migration ADR when any trigger in `config/scale-policy.json` is crossed:

- 50,000 candidate records;
- 150,000 candidate lifecycle JSON files;
- 100,000 seen source items;
- 32 MiB harvest state;
- or 60 seconds for full repository validation on the reference workflow.

Crossing one trigger starts evaluation; it does not silently migrate. SQLite is the local-first default for hot state. Parquet is considered only for cold analytical evidence. A search/vector index remains derived.

## Benchmark protocol

`python scripts/benchmark_storage.py --root . --records 10000`:

- inventories actual repository record sizes;
- creates synthetic candidate/review/decision files only in a temporary directory;
- measures write and parse enumeration in one Python process;
- projects configured target sizes;
- evaluates migration triggers;
- prints JSON and persists nothing.

CI uses a smaller deterministic fixture to prove the benchmark remains runnable without treating noisy wall-clock values as release gates.

## Measured benchmark results

| Lifecycle records | Files | Synthetic bytes | Write | Parse/enumerate |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 300 | 50,100 | 0.094 s | 3.703 s |
| 10,000 | 30,000 | 5,010,000 | 14.768 s | 524.405 s |

The fixture deliberately keeps each JSON payload small, so these timings isolate the current three-files-per-lifecycle traversal shape rather than reproduce the projected 37.6 MB of real candidate payload. The 10,000-record result confirms that filesystem enumeration, per-file open/parse work, Git metadata, and local antivirus effects can dominate raw bytes.

The same benchmark command measured current in-process full repository validation at 0.178 seconds and passed that value into trigger evaluation. At the time, this did not trigger an immediate migration: the real repository still had 110 candidate records, 330 lifecycle files, a 21,772-byte harvest state, 100 seen source items, and no active trigger. The 30,000-file benchmark nevertheless exposed the filesystem traversal bottleneck that ADR-002 later used for the SQLite cutover.

## 2026-08-29 cutover

ADR-002 supersedes the historical decision above. The one-time import recorded 13 source states, 110 discoveries, and 110 decisions with legacy digest `ddfc0fa74dfef3ab56644445aba527c00935658a9446150155e9b88ccb883de9`. Active JSON lifecycle files are removed at cutover; Git history and the migration manifest preserve the audit trail. The active benchmark now measures SQLite reads/writes and retains the JSON benchmark only as a historical baseline.

## Limitations

- Initial shell timings included Windows sandbox and process startup, so they are not used as algorithmic results.
- Benchmark wall time is environment-specific and is not a portable throughput guarantee or a CI pass/fail threshold.
- Projections are planning evidence, not throughput guarantees.
- Semantic-review time and model cost are unavailable without a trusted runtime meter and are not estimated.
