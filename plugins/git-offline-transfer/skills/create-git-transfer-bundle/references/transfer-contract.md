# Git bundle transfer contract

## What the artifact contains

A full bundle created with `--all` carries objects reachable from the repository's advertised refs. Verification checks the bundle structure and any declared prerequisite commits. `git bundle list-heads` shows the refs a receiver can address.

It does not capture the working tree, index-only changes, untracked or ignored files, reflog-only commits, external Git LFS objects, submodule working trees, hooks, repository configuration, or credentials. Handle those separately and describe them explicitly.

## Receiver plan

- For a self-contained bundle, propose `git clone PATH/repository.bundle DESTINATION`.
- For an existing repository, first verify the bundle in that repository, inspect advertised refs, and then propose a named `git fetch PATH/repository.bundle REF:REF` operation.
- A bundle is not a push destination. Create a new bundle for later incremental transfer.

Do not create an incremental bundle unless the receiver's prerequisite commits are known and verification succeeds in the receiver repository. Keep the source until the receiver has independently cloned or fetched and checked the expected refs.
