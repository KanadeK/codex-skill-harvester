# Ansible collection validation contract

## Required boundary

Run `ansible-test` from a collection root laid out as `ansible_collections/<namespace>/<collection>`. The namespace and collection name in `galaxy.yml` or `galaxy.yaml` must match that path. Sanity, unit, and integration tests are distinct layers; the presence of one does not prove another passed.

The deterministic planner only discovers those layers. It does not prove that Ansible, Docker, dependencies, or target ansible-core versions are installed and compatible.

## Execution decisions

- Run sanity for every collection change.
- Run units when `tests/unit` exists and the change can affect tested Python behavior.
- Run integration when `tests/integration/targets` exists and the change affects an integration target or its shared behavior.
- Use only project-declared ansible-core versions. Record each version and environment separately.
- Docker execution is a local side effect and may download images; obtain approval and follow the repository's documented environment policy.

Do not execute playbooks against remote inventories, install arbitrary roles or collections, publish to Galaxy, merge a pull request, or push a release as part of this validation workflow.
