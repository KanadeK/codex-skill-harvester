#!/usr/bin/env python3
"""Inspect an npm package dry-run payload without scripts or network access."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


MAX_PACKAGE_JSON_BYTES = 1_000_000
MAX_REPORT_BYTES = 5_000_000
MAX_FILES = 20_000
MAX_UNPACKED_BYTES = 500_000_000
LIFECYCLE_SCRIPTS = {
    "prepack",
    "prepare",
    "postpack",
    "prepublish",
    "prepublishOnly",
    "publish",
    "postpublish",
}
SENSITIVE_NAMES = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
SENSITIVE_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}


class AuditError(ValueError):
    pass


def _git_tracked(root: Path, files: list[str]) -> list[str] | None:
    git = shutil.which("git")
    if git is None:
        return None
    inside = subprocess.run(
        [git, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if inside.returncode or inside.stdout.strip() != "true":
        return None
    untracked = []
    for name in files:
        checked = subprocess.run(
            [git, "-C", str(root), "ls-files", "--error-unmatch", "--", name],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if checked.returncode:
            untracked.append(name)
    return untracked


def inspect(root_path: Path) -> dict[str, object]:
    root = root_path.resolve()
    package_json = root / "package.json"
    if not root.is_dir() or not package_json.is_file():
        raise AuditError("package root must be a directory containing package.json")
    if package_json.stat().st_size > MAX_PACKAGE_JSON_BYTES:
        raise AuditError(f"package.json exceeds {MAX_PACKAGE_JSON_BYTES} bytes")
    try:
        metadata = json.loads(package_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise AuditError(f"package.json is not valid UTF-8 JSON: {error}") from error
    if not isinstance(metadata, dict):
        raise AuditError("package.json must contain a JSON object")
    npm = shutil.which("npm")
    if npm is None:
        raise AuditError("npm executable was not found")

    with tempfile.TemporaryDirectory(prefix="npm-readiness-") as temporary:
        cache = Path(temporary) / "cache"
        environment = dict(os.environ)
        environment.update(
            {
                "npm_config_cache": str(cache),
                "npm_config_ignore_scripts": "true",
                "npm_config_offline": "true",
                "npm_config_audit": "false",
                "npm_config_fund": "false",
            }
        )
        completed = subprocess.run(
            [
                npm,
                "pack",
                "--dry-run",
                "--json",
                "--ignore-scripts",
                "--offline",
                "--cache",
                str(cache),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise AuditError(f"npm pack dry-run failed ({completed.returncode}): {detail}")
    if len(completed.stdout.encode("utf-8")) > MAX_REPORT_BYTES:
        raise AuditError(f"npm pack JSON exceeds {MAX_REPORT_BYTES} bytes")
    try:
        payloads = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AuditError(f"npm pack did not return valid JSON: {error}") from error
    if not isinstance(payloads, list) or len(payloads) != 1:
        raise AuditError("npm pack must return exactly one package payload")
    payload = payloads[0]
    raw_files = payload.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise AuditError("npm pack returned an empty or invalid file list")
    if len(raw_files) > MAX_FILES:
        raise AuditError(f"npm package contains more than {MAX_FILES} files")
    files = []
    total_bytes = 0
    sensitive = []
    for item in raw_files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise AuditError("npm pack file entries must contain paths")
        path = PurePosixPath(item["path"])
        if path.is_absolute() or ".." in path.parts:
            raise AuditError(f"npm pack returned an unsafe path: {item['path']}")
        size = item.get("size", 0)
        if not isinstance(size, int) or size < 0:
            raise AuditError(f"npm pack returned an invalid size for {item['path']}")
        total_bytes += size
        files.append(item["path"])
        lowered = {part.lower() for part in path.parts}
        if lowered & SENSITIVE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES:
            sensitive.append(item["path"])
    if total_bytes > MAX_UNPACKED_BYTES:
        raise AuditError(f"npm package payload exceeds {MAX_UNPACKED_BYTES} bytes")

    failures = []
    warnings = []
    name = metadata.get("name")
    version = metadata.get("version")
    if not isinstance(name, str) or not name.strip():
        failures.append("package.json name is missing")
    if not isinstance(version, str) or not version.strip():
        failures.append("package.json version is missing")
    if metadata.get("private") is True:
        failures.append("package.json private is true")
    if isinstance(name, str) and payload.get("name") != name:
        failures.append("npm pack name does not match package.json")
    if isinstance(version, str) and payload.get("version") != version:
        failures.append("npm pack version does not match package.json")
    if sensitive:
        failures.append("payload includes credential-like or private-key filenames")

    types_value = metadata.get("types")
    typings_value = metadata.get("typings")
    if types_value is not None and not isinstance(types_value, str):
        failures.append("package.json types must be a string")
    if typings_value is not None and not isinstance(typings_value, str):
        failures.append("package.json typings must be a string")
    if (
        isinstance(types_value, str)
        and isinstance(typings_value, str)
        and PurePosixPath(types_value) != PurePosixPath(typings_value)
    ):
        failures.append("package.json types and typings point to different files")
    raw_declaration_entry = (
        types_value if isinstance(types_value, str) else typings_value
        if isinstance(typings_value, str)
        else None
    )
    declaration_entry = None
    entry_in_payload = None
    if raw_declaration_entry is not None:
        candidate_entry = PurePosixPath(raw_declaration_entry.replace("\\", "/"))
        if candidate_entry.is_absolute() or ".." in candidate_entry.parts:
            failures.append("declared types entry has an unsafe path")
        else:
            declaration_entry = candidate_entry.as_posix()
            entry_in_payload = declaration_entry in files
            if not entry_in_payload:
                failures.append("declared types entry is absent from the npm payload")
    types_versions = metadata.get("typesVersions")
    if types_versions is not None and not isinstance(types_versions, dict):
        failures.append("package.json typesVersions must be an object")
    declaration_files = sorted(
        name for name in files if name.endswith((".d.ts", ".d.mts", ".d.cts"))
    )
    scripts = metadata.get("scripts", {})
    declared_lifecycle = sorted(
        key for key in LIFECYCLE_SCRIPTS if isinstance(scripts, dict) and key in scripts
    )
    if declared_lifecycle:
        warnings.append("release lifecycle scripts were declared but not executed")
    untracked = _git_tracked(root, files)
    if untracked:
        failures.append("payload includes files not tracked by Git")
    elif untracked is None:
        warnings.append("Git tracking could not be verified")
    status = "not-ready" if failures else "unverified" if warnings else "ready"
    return {
        "status": status,
        "package": {"name": name, "version": version},
        "payload": {
            "file_count": len(files),
            "unpacked_bytes": total_bytes,
            "files": files,
        },
        "failures": failures,
        "warnings": warnings,
        "declared_lifecycle_scripts": declared_lifecycle,
        "declarations": {
            "entry": declaration_entry,
            "entry_in_payload": entry_in_payload,
            "files": declaration_files,
            "types_versions_declared": isinstance(types_versions, dict),
        },
        "sensitive_paths": sensitive,
        "untracked_paths": untracked,
        "protections": {
            "dry_run": True,
            "ignore_scripts": True,
            "offline": True,
            "temporary_cache": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (AuditError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
