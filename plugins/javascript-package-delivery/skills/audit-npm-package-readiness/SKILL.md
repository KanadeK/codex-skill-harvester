---
name: audit-npm-package-readiness
description: "Audit an npm package payload and publication configuration before release. Use when asked what npm pack will include, whether a Node.js package is ready to publish, whether TypeScript declarations are present in the package, or whether package metadata and lifecycle boundaries are safe. Do not use to install dependencies, execute lifecycle scripts, publish to a registry, change package files, or audit an already-published release."
---

# Audit Npm Package Readiness

Perform a local, pre-publication audit. Never run package lifecycle scripts, install dependencies, contact a registry, print npm credentials, change the package, or call `npm publish`.

## Gather inputs

Identify the exact package root and its `package.json`. For a workspace, identify one package at a time; do not assume the workspace root is what will be published. State whether the source is a Git repository and whether the tree is clean.

## Inspect the dry-run payload

Run the bundled checker from an isolated temporary working directory:

`python scripts/inspect_npm_package.py --root PATH`

The checker bounds and parses `package.json`, runs local `npm pack --dry-run --json` with lifecycle scripts disabled, offline mode enabled, and a temporary npm cache, then checks package identity, privacy, payload size, sensitive filenames, lifecycle-script declarations, Git tracking when available, and whether a declared `types` or `typings` entry is present in the exact payload. It does not create a tarball.

A nonzero exit means the package is `not-ready` or `unverified`. Never rerun without the script and offline protections merely to get a passing result.

## Review manual gates

Use [the package contract](references/package-contract.md) to review README and license inclusion, workspace selection, registry scope and access, provenance policy, supported Node versions, declaration compatibility with the runtime API, consumer import fixtures, `typesVersions`, and whether declared lifecycle scripts have independent trusted test evidence. Treat a dry-run payload as evidence of package contents, not authorization to publish or proof that declarations are semantically correct.

## Report

Lead with `ready`, `not-ready`, or `unverified`. List the exact payload size and files, deterministic failures, warnings, skipped manual gates, and smallest next action. Do not edit, version, tag, upload, or publish as part of this Skill.
