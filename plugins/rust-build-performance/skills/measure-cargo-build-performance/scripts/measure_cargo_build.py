#!/usr/bin/env python3
"""Measure cold and warm offline Cargo builds in a temporary target directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class MeasurementError(ValueError):
    pass


def measure(repo_path: Path, package: str | None, release: bool) -> dict[str, object]:
    repo = repo_path.resolve()
    manifest = repo / "Cargo.toml"
    lockfile = repo / "Cargo.lock"
    if not repo.is_dir() or not manifest.is_file():
        raise MeasurementError("repository must contain Cargo.toml")
    if not lockfile.is_file():
        raise MeasurementError("Cargo.lock is required to prevent dependency drift")
    cargo = shutil.which("cargo")
    if cargo is None:
        raise MeasurementError("cargo executable was not found")
    command = [cargo, "build", "--offline", "--locked"]
    if package:
        command.extend(["--package", package])
    if release:
        command.append("--release")
    durations = []
    outputs = []
    with tempfile.TemporaryDirectory(prefix="cargo-measure-") as target:
        environment = dict(os.environ)
        environment["CARGO_TARGET_DIR"] = target
        for phase in ("cold", "warm"):
            started = time.perf_counter()
            completed = subprocess.run(
                command,
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=900,
            )
            elapsed = time.perf_counter() - started
            if completed.returncode:
                detail = completed.stderr.strip() or completed.stdout.strip()
                raise MeasurementError(
                    f"{phase} Cargo build failed ({completed.returncode}): {detail}"
                )
            durations.append(round(elapsed, 6))
            outputs.append(
                {
                    "phase": phase,
                    "seconds": round(elapsed, 6),
                    "stderr_tail": completed.stderr.splitlines()[-20:],
                }
            )
    return {
        "status": "measured",
        "repository": str(repo),
        "package": package,
        "profile": "release" if release else "dev",
        "command": [Path(command[0]).name, *command[1:]],
        "runs": outputs,
        "warm_to_cold_ratio": round(durations[1] / durations[0], 6),
        "protections": {
            "offline": True,
            "locked": True,
            "temporary_target_directory": True,
            "cargo_clean": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--package")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = measure(args.repo, args.package, args.release)
    except (MeasurementError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
