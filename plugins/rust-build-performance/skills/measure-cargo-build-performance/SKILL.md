---
name: measure-cargo-build-performance
description: "Measure and diagnose Cargo build performance with reproducible cold and warm builds in an isolated target directory. Use when a Rust workspace builds slowly or when evaluating Cargo cache and configuration changes. Do not use for runtime profiling, crate publication, dependency upgrades, destructive cargo clean operations, or builds the user has not authorized."
---

# Measure Cargo Build Performance

Builds can execute `build.rs`, procedural macros, and compiler plugins from the repository and its dependencies. Treat the project as untrusted and obtain explicit approval before invoking Cargo. Never use this Skill during public-evidence harvesting.

## Establish the experiment

Identify the workspace or package, expected target/profile, existing `Cargo.lock`, current Cargo configuration, and the performance question. Require a clean or intentionally dirty tree and record its state. Do not edit configuration before collecting a baseline.

## Measure

Run the bundled measurer from an isolated temporary working directory:

`python scripts/measure_cargo_build.py --repo PATH [--package NAME] [--release]`

The script requires `Cargo.lock`, runs two offline Cargo builds against one temporary `CARGO_TARGET_DIR`, and reports cold and warm wall-clock times plus the exact command. It never calls `cargo clean`, publishes, changes dependencies, or retains build artifacts. A missing offline dependency fails instead of contacting a registry.

Read [the measurement contract](references/measurement-contract.md) before changing profiles, linker settings, codegen units, features, or global Cargo configuration.

## Diagnose and compare

Use the first measurement as a baseline, not a verdict. Inspect Cargo timing evidence and effective configuration, select one bounded hypothesis, repeat the same experiment, and compare like-for-like. Do not claim an improvement from a single noisy run or compare different package, feature, target, or profile sets.

## Report

Report environment, package scope, exact command, cold/warm durations, ratio, failed or skipped evidence, and the next single experiment. Separate measured facts from hypotheses. Never publish a crate or persist a configuration change without separate authorization.
