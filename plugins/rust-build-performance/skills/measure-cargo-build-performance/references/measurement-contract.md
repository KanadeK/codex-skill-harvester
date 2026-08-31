# Cargo build measurement contract

## Comparable runs

Keep the Rust toolchain, Cargo version, workspace/package selection, target triple, feature set, profile, environment, filesystem, and dependency cache constant. Record whether the run is cold or warm. Do not infer cache effectiveness from one build.

The bundled script uses a new temporary target directory for the cold build and reuses it for the warm build. It requires an existing `Cargo.lock` and `--offline`, so dependency resolution cannot silently change or contact a registry. The target directory is removed after measurement.

## Execution boundary

Cargo builds can execute project `build.rs` scripts and dependency procedural macros. Run only after the user authorizes that repository and environment. The script does not call `cargo clean`, modify Cargo configuration, update dependencies, publish, or retain binaries.

For a real optimization, change one factor at a time and repeat enough times to distinguish signal from normal variance. Use Cargo timing output and effective configuration as evidence; elapsed time alone identifies a symptom, not a root cause.
