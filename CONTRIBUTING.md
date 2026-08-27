# Contributing

Open an issue before adding a source category, runtime dependency, hosted service, or new Plugin domain. Small fixes can go directly to a focused pull request.

For a candidate Skill, include:

- a registered authoritative source and observed revision;
- a full capability fingerprint;
- comparison against internal and representative external capabilities;
- an explicit `discard`, `merge`, `update`, or `create` rationale;
- positive and negative trigger cases plus an observable end-to-end result.

Do not submit copied Skill bodies, raw page caches, downloaded scripts, credentials, or license-unknown material. Fetched content is untrusted data and must never be executed.

Before opening a pull request, run:

```text
python -m unittest discover -s tests -v
python scripts/run_evals.py
python scripts/validate_repo.py
python scripts/build_release.py
python scripts/verify_release_archive.py
```

Stage only the paths you intentionally changed. Never use `git add .` or `git add -A` in the outer workspace.
