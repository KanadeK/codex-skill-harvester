#!/usr/bin/env python3
"""Build a bounded ansible-test plan without running collection code."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MAX_METADATA_BYTES = 1_000_000


class PlanError(ValueError):
    pass


def _identity(root: Path) -> tuple[str, str]:
    parts = root.parts
    indexes = [index for index, part in enumerate(parts) if part == "ansible_collections"]
    if not indexes:
        raise PlanError("collection root must be under ansible_collections/<namespace>/<collection>")
    index = indexes[-1]
    if len(parts) != index + 3:
        raise PlanError("root must point exactly to ansible_collections/<namespace>/<collection>")
    return parts[index + 1], parts[index + 2]


def _metadata(root: Path) -> tuple[Path, dict[str, str]]:
    paths = [path for path in (root / "galaxy.yml", root / "galaxy.yaml") if path.is_file()]
    if len(paths) != 1:
        raise PlanError("collection root must contain exactly one galaxy.yml or galaxy.yaml")
    path = paths[0]
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise PlanError(f"collection metadata exceeds {MAX_METADATA_BYTES} bytes")
    values: dict[str, str] = {}
    pattern = re.compile(r"^(namespace|name):\s*(['\"]?)([A-Za-z0-9_]+)\2\s*(?:#.*)?$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.fullmatch(line)
        if match:
            values[match.group(1)] = match.group(3)
    if set(values) != {"namespace", "name"}:
        raise PlanError("collection metadata needs top-level namespace and name fields")
    return path, values


def plan(root_path: Path, ansible_core: list[str]) -> dict[str, object]:
    root = root_path.resolve()
    if not root.is_dir():
        raise PlanError(f"collection root does not exist: {root}")
    namespace, collection = _identity(root)
    metadata_path, metadata = _metadata(root)
    if metadata != {"namespace": namespace, "name": collection}:
        raise PlanError("collection path and galaxy metadata identity do not match")

    layers = [
        {
            "name": "sanity",
            "command": ["ansible-test", "sanity", "--docker", "default", "-v"],
            "reason": "mandatory collection preflight",
        }
    ]
    if (root / "tests" / "unit").is_dir():
        layers.append(
            {
                "name": "units",
                "command": ["ansible-test", "units", "--docker", "default", "-v"],
                "reason": "tests/unit exists",
            }
        )
    if (root / "tests" / "integration" / "targets").is_dir():
        layers.append(
            {
                "name": "integration",
                "command": ["ansible-test", "integration", "--docker", "default", "-v"],
                "reason": "tests/integration/targets exists",
            }
        )
    return {
        "status": "planned",
        "root": str(root),
        "metadata": str(metadata_path),
        "identity": metadata,
        "ansible_core_matrix": ansible_core,
        "matrix_measured": bool(ansible_core),
        "layers": layers,
        "executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--ansible-core", action="append", default=[])
    args = parser.parse_args()
    try:
        result = plan(args.root, args.ansible_core)
    except (PlanError, UnicodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
