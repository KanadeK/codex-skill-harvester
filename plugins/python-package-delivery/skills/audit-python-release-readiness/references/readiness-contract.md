# Python release readiness contract

Use this reference after the deterministic checker. It is an original synthesis of necessary facts from the registered PyPA, PyPI, and GitHub sources; it does not reproduce source instructions.

## Artifact gates

- Expect at least one source distribution and the wheels required by the project's supported platforms.
- Require project name and version to agree across `pyproject.toml`, archive filenames, `PKG-INFO`, and wheel `METADATA`.
- A modern sdist should contain one name-version root with `pyproject.toml` and `PKG-INFO`. Inspect member paths without extracting the archive.
- A wheel should contain one matching `.dist-info` directory with `METADATA`, `WHEEL`, and `RECORD`. Compatibility tags are a support claim; compare them with the release's intended Python, ABI, and platform matrix.
- Fail closed before expensive archive work: inspect at most 128 distribution files and 1 GiB of aggregate archive bytes; per archive, allow at most 512 MiB compressed bytes, 10,000 members, and 512 MiB declared expanded bytes; read at most 1 MiB from `PKG-INFO`/`METADATA` and 8 MiB from `RECORD`. These are checker resource boundaries, not Python packaging format limits.
- A structural pass does not prove that the package imports or behaves correctly. Record isolated local-wheel installation and an authorized smoke check separately when required.

## Publishing workflow gates

- Build artifacts in a job that cannot publish, then pass those exact artifacts to a separate publishing job.
- Prefer PyPI Trusted Publishing over a long-lived upload token. Only the publishing job's own `permissions.id-token: write` satisfies this audit; top-level permissions and values under `env`, steps, comments, strings, or another job do not. Keep the publishing job minimal.
- Check that the registered owner, repository, workflow filename, and optional environment match the actual workflow. Review production environment approval and tag protection according to the project's threat model.
- Reject workflows that expose a PyPI password or long-lived API token when the intended design is Trusted Publishing.
- The official PyPA publishing action can generate PyPI attestations by default. Record whether that feature is expected, but do not describe it as vulnerability or malware assurance.

## Conditional gates

- TestPyPI is useful for pre-production installation evidence but is a separate, disposable service. State the dependency-index policy explicitly; do not silently mix indexes.
- Generic GitHub artifact attestations are valuable only when verified against a stated owner or repository policy. Attestation verification links an artifact to source and build information; it does not establish that the artifact is safe.
- Dynamic versions, platform-specific wheel matrices, compiled extensions, and non-GitHub publishers need toolchain-specific evidence. Mark them `unverified` rather than guessing.

## Registered evidence

The relevant registry ids are `pypa-source-distribution-spec`, `pypa-wheel-spec`, `pypa-core-metadata`, `pypa-build-readme`, `pypa-packaging-tutorial`, `pypa-publish-github-actions`, `pypa-testpypi`, `pypa-twine-readme`, `pypa-publish-action-readme`, `pypi-trusted-publisher-use`, `pypi-trusted-publisher-security`, and `pypi-attestations-produce`.
