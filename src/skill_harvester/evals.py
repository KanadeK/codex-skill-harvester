from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

from .io import load_json


class EvalError(ValueError):
    pass


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise EvalError(f"eval path escapes the repository: {relative}")
    return path


def _run(
    command: list[str], temporary_directory: Path
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        command,
        cwd=temporary_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _github_release_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    snapshot = _inside(root, end_to_end["snapshot"])
    output = temporary_directory / "release-audit.md"
    completed = _run(
        [sys.executable, str(script), str(snapshot), "--output", str(output)],
        temporary_directory,
    )
    markdown = output.read_text(encoding="utf-8")
    result = markdown.splitlines()[0].removeprefix("# Release audit: ")
    gate_count = sum(
        line.startswith("| ")
        and not line.startswith("| Gate ")
        and not line.startswith("| --- ")
        for line in markdown.splitlines()
    )
    if gate_count != end_to_end["expected_gates"]:
        raise EvalError("end-to-end report gate count did not match")
    return completed, output, result, gate_count


def _tar_member(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    archive.addfile(member, io.BytesIO(data))


def _python_release_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    fixture = load_json(_inside(root, end_to_end["fixture"]))
    name = fixture["project_name"]
    normalized_name = name.replace("-", "_")
    version = fixture["version"]
    project = temporary_directory / "python-release-fixture"
    dist = project / "dist"
    dist.mkdir(parents=True)
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "{name}"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    sdist_root = f"{normalized_name}-{version}"
    with tarfile.open(dist / f"{sdist_root}.tar.gz", "w:gz") as archive:
        _tar_member(archive, f"{sdist_root}/pyproject.toml", pyproject.read_bytes())
        _tar_member(
            archive,
            f"{sdist_root}/PKG-INFO",
            (
                f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"
            ).encode(),
        )
    dist_info = f"{normalized_name}-{version}.dist-info"
    entries = {
        f"{normalized_name}/__init__.py": b"",
        f"{dist_info}/METADATA": (
            f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"
        ).encode(),
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
    }
    record_path = f"{dist_info}/RECORD"
    entries[record_path] = "".join(
        f"{entry},,\n" for entry in [*entries, record_path]
    ).encode()
    with zipfile.ZipFile(
        dist / f"{normalized_name}-{version}-py3-none-any.whl", "w"
    ) as archive:
        for entry, data in entries.items():
            archive.writestr(entry, data)
    workflow = project / "release.yml"
    workflow.write_text(fixture["workflow"], encoding="utf-8")
    output = temporary_directory / "python-release-readiness.md"
    completed = _run(
        [
            sys.executable,
            str(script),
            "--pyproject",
            str(pyproject),
            "--dist",
            str(dist),
            "--workflow",
            str(workflow),
            "--output",
            str(output),
        ],
        temporary_directory,
    )
    markdown = output.read_text(encoding="utf-8")
    result = markdown.splitlines()[0].removeprefix(
        "# Python release readiness: "
    )
    gate_count = sum(
        line.startswith("| ")
        and not line.startswith("| Check ")
        and not line.startswith("| --- ")
        for line in markdown.splitlines()
    )
    if gate_count < end_to_end["minimum_gates"]:
        raise EvalError("end-to-end report omitted required readiness gates")
    return completed, output, result, gate_count


def run_eval_file(root: Path, eval_path: Path, temporary_directory: Path) -> dict[str, Any]:
    value = load_json(eval_path)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise EvalError("eval must use schema_version 1")
    if value.get("reviewed_by") != "codex":
        raise EvalError("semantic trigger cases must be reviewed_by codex")
    cases = value.get("trigger_cases")
    if not isinstance(cases, list) or not cases:
        raise EvalError("eval must contain trigger cases")
    for case in cases:
        if case["expected"] not in {"trigger", "do-not-trigger"}:
            raise EvalError("trigger case has an unsupported expectation")
        if case["observed"] != case["expected"]:
            raise EvalError(f"trigger case failed: {case['id']}")
        if len(case["rationale"].strip()) < 20:
            raise EvalError(f"trigger case needs a concrete rationale: {case['id']}")

    end_to_end = value["end_to_end"]
    kind = end_to_end.get("kind")
    if kind == "github-release-snapshot":
        completed, output, result, gate_count = _github_release_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "python-release-readiness":
        completed, output, result, gate_count = _python_release_e2e(
            root, end_to_end, temporary_directory
        )
    else:
        raise EvalError(f"unsupported end-to-end kind: {kind!r}")
    if completed.returncode != end_to_end["expected_exit_code"]:
        raise EvalError(
            f"end-to-end script exited {completed.returncode}: {completed.stderr.strip()}"
        )
    if result != end_to_end["expected_result"]:
        raise EvalError("end-to-end report did not match the expected result")
    positive = sum(case["expected"] == "trigger" for case in cases)
    return {
        "capability_id": value["capability_id"],
        "trigger_cases": len(cases),
        "positive": positive,
        "negative": len(cases) - positive,
        "e2e_result": result,
        "e2e_gates": gate_count,
        "report_path": str(output),
    }
