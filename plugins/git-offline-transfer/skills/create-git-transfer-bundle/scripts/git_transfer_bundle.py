#!/usr/bin/env python3
"""Create or verify a Git bundle without executing repository content."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


class BundleError(ValueError):
    pass


def _git(arguments: list[str], *, repo: Path | None = None) -> str:
    command = ["git"]
    if repo is not None:
        command.extend(["-C", str(repo)])
    command.extend(arguments)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BundleError(f"git command failed ({completed.returncode}): {detail}")
    return completed.stdout


def _repository(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise BundleError(f"repository directory does not exist: {resolved}")
    top = Path(_git(["rev-parse", "--show-toplevel"], repo=resolved).strip()).resolve()
    return top


def _heads(bundle: Path) -> list[dict[str, str]]:
    heads = []
    for line in _git(["bundle", "list-heads", str(bundle)]).splitlines():
        object_id, ref = line.split(maxsplit=1)
        heads.append({"object_id": object_id, "ref": ref})
    if not heads:
        raise BundleError("bundle advertises no refs")
    return heads


def _verify(repo: Path, bundle: Path) -> dict[str, object]:
    if not bundle.is_file():
        raise BundleError(f"bundle file does not exist: {bundle}")
    verification = _git(["bundle", "verify", str(bundle)], repo=repo)
    return {
        "status": "verified",
        "repository": str(repo),
        "bundle": str(bundle),
        "advertised_refs": _heads(bundle),
        "verification": [line for line in verification.splitlines() if line.strip()],
        "excludes": [
            "uncommitted and untracked files",
            "ignored files and working-tree state",
            "external Git LFS objects",
            "submodule working trees",
        ],
    }


def create(repo_path: Path, output_path: Path) -> dict[str, object]:
    repo = _repository(repo_path)
    output = output_path.resolve()
    if output.exists():
        raise BundleError(f"refusing to overwrite existing path: {output}")
    dirty = _git(["status", "--porcelain", "--untracked-files=all"], repo=repo)
    if dirty.strip():
        raise BundleError("repository is not clean; commit or preserve all work before bundling")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        _git(["bundle", "create", str(temporary), "--all"], repo=repo)
        result = _verify(repo, temporary)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    result["bundle"] = str(output)
    result["mode"] = "create"
    return result


def verify(repo_path: Path, bundle_path: Path) -> dict[str, object]:
    result = _verify(_repository(repo_path), bundle_path.resolve())
    result["mode"] = "verify"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create", help="create and verify a full bundle")
    create_parser.add_argument("--repo", type=Path, required=True)
    create_parser.add_argument("--output", type=Path, required=True)
    verify_parser = commands.add_parser("verify", help="verify an existing bundle")
    verify_parser.add_argument("--repo", type=Path, required=True)
    verify_parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            create(args.repo, args.output)
            if args.command == "create"
            else verify(args.repo, args.bundle)
        )
    except (BundleError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
