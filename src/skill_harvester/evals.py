from __future__ import annotations

import io
import json
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


def _git_transfer_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    source = temporary_directory / "source"
    source.mkdir()
    for command in (
        ["git", "-C", str(source), "init"],
        ["git", "-C", str(source), "config", "user.name", "Eval Author"],
        ["git", "-C", str(source), "config", "user.email", "eval@example.invalid"],
    ):
        prepared = _run(command, temporary_directory)
        if prepared.returncode:
            raise EvalError(f"Git fixture setup failed: {prepared.stderr.strip()}")
    (source / "tracked.txt").write_text("committed fixture\n", encoding="utf-8")
    for command in (
        ["git", "-C", str(source), "add", "tracked.txt"],
        ["git", "-C", str(source), "commit", "-m", "fixture"],
        ["git", "-C", str(source), "branch", "retained-branch"],
    ):
        prepared = _run(command, temporary_directory)
        if prepared.returncode:
            raise EvalError(f"Git fixture setup failed: {prepared.stderr.strip()}")

    bundle = temporary_directory / "transfer.bundle"
    completed = _run(
        [
            sys.executable,
            str(script),
            "create",
            "--repo",
            str(source),
            "--output",
            str(bundle),
        ],
        temporary_directory,
    )
    output = temporary_directory / "git-transfer-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    if completed.returncode:
        return completed, output, "failed", 0
    payload = json.loads(completed.stdout)
    receiver = temporary_directory / "receiver"
    cloned = _run(["git", "clone", str(bundle), str(receiver)], temporary_directory)
    if cloned.returncode:
        raise EvalError(f"bundle clone failed: {cloned.stderr.strip()}")
    source_revisions = _run(
        ["git", "-C", str(source), "rev-list", "--all"], temporary_directory
    )
    receiver_revisions = _run(
        ["git", "-C", str(receiver), "rev-list", "--all"], temporary_directory
    )
    if source_revisions.returncode or receiver_revisions.returncode:
        raise EvalError("could not inspect source and receiver revisions")
    gates = [
        bundle.is_file(),
        bool(payload.get("advertised_refs")),
        set(source_revisions.stdout.splitlines())
        == set(receiver_revisions.stdout.splitlines()),
    ]
    if not all(gates):
        raise EvalError("bundle E2E did not preserve all committed revisions")
    return completed, output, payload["status"], len(gates)


def _ansible_collection_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    collection = (
        temporary_directory / "ansible_collections" / "acme" / "widgets"
    )
    (collection / "tests" / "unit").mkdir(parents=True)
    (collection / "tests" / "integration" / "targets").mkdir(parents=True)
    (collection / "galaxy.yml").write_text(
        "namespace: acme\nname: widgets\nversion: 1.0.0\n",
        encoding="utf-8",
    )
    completed = _run(
        [
            sys.executable,
            str(script),
            "--root",
            str(collection),
            "--ansible-core",
            "2.18",
        ],
        temporary_directory,
    )
    output = temporary_directory / "ansible-collection-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    if completed.returncode:
        return completed, output, "failed", 0
    payload = json.loads(completed.stdout)
    layers = [layer["name"] for layer in payload["layers"]]
    if layers != ["sanity", "units", "integration"] or payload["executed"]:
        raise EvalError("collection E2E plan did not preserve its bounded execution contract")
    return completed, output, payload["status"], len(layers)


def _npm_package_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    package = temporary_directory / "npm-package"
    package.mkdir()
    (package / "package.json").write_text(
        json.dumps(
            {
                "name": "harvester-eval-package",
                "version": "1.0.0",
                "files": ["index.js", "README.md", "LICENSE"],
                "license": "MIT",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (package / "index.js").write_text("export const value = 1;\n", encoding="utf-8")
    (package / "README.md").write_text("# Eval package\n", encoding="utf-8")
    (package / "LICENSE").write_text("Evaluation fixture\n", encoding="utf-8")
    for command in (
        ["git", "-C", str(package), "init"],
        ["git", "-C", str(package), "config", "user.name", "Eval Author"],
        ["git", "-C", str(package), "config", "user.email", "eval@example.invalid"],
        ["git", "-C", str(package), "add", "package.json", "index.js", "README.md", "LICENSE"],
        ["git", "-C", str(package), "commit", "-m", "fixture"],
    ):
        prepared = _run(command, temporary_directory)
        if prepared.returncode:
            raise EvalError(f"npm fixture setup failed: {prepared.stderr.strip()}")
    completed = _run(
        [sys.executable, str(script), "--root", str(package)],
        temporary_directory,
    )
    output = temporary_directory / "npm-package-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    if completed.returncode:
        return completed, output, "failed", 0
    payload = json.loads(completed.stdout)
    gates = [
        payload["protections"]["ignore_scripts"],
        payload["protections"]["offline"],
        payload["payload"]["file_count"] >= 3,
        not payload["sensitive_paths"],
    ]
    if not all(gates):
        raise EvalError("npm package E2E omitted a required safety gate")
    return completed, output, payload["status"], len(gates)


def _cargo_performance_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    crate = temporary_directory / "cargo-crate"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "harvester_eval_crate"\nversion = "0.1.0"\nedition = "2021"\n',
        encoding="utf-8",
    )
    (crate / "Cargo.lock").write_text(
        'version = 4\n\n[[package]]\nname = "harvester_eval_crate"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (crate / "src" / "lib.rs").write_text(
        "pub fn answer() -> u32 { 42 }\n", encoding="utf-8"
    )
    completed = _run(
        [sys.executable, str(script), "--repo", str(crate)],
        temporary_directory,
    )
    output = temporary_directory / "cargo-performance-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    if completed.returncode:
        return completed, output, "failed", 0
    payload = json.loads(completed.stdout)
    gates = [
        [run["phase"] for run in payload["runs"]] == ["cold", "warm"],
        payload["protections"]["offline"],
        payload["protections"]["locked"],
        payload["protections"]["temporary_target_directory"],
        not (crate / "target").exists(),
    ]
    if not all(gates):
        raise EvalError("Cargo performance E2E violated its isolation contract")
    return completed, output, payload["status"], len(gates)


def _cors_diagnosis_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    evidence = temporary_directory / "cors-evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "page_origin": "https://app.example",
                "request": {
                    "url": "https://api.example/items",
                    "method": "POST",
                    "mode": "cors",
                    "credentials": "include",
                    "headers": {"content-type": "application/json"},
                },
                "preflight": {
                    "status": 204,
                    "headers": {
                        "access-control-allow-origin": "https://app.example",
                        "access-control-allow-credentials": "true",
                        "access-control-allow-methods": "POST",
                        "access-control-allow-headers": "content-type",
                    },
                },
                "response": {
                    "status": 200,
                    "headers": {
                        "access-control-allow-origin": "*",
                        "access-control-allow-credentials": "true",
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    completed = _run(
        [sys.executable, str(script), "--input", str(evidence)],
        temporary_directory,
    )
    output = temporary_directory / "cors-diagnosis-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    payload = json.loads(completed.stdout)
    gate_count = len(payload["findings"])
    if not gate_count:
        raise EvalError("CORS diagnosis E2E did not identify the unsafe credentialed wildcard")
    return completed, output, payload["status"], gate_count


def _curl_request_e2e(
    root: Path, end_to_end: dict[str, Any], temporary_directory: Path
) -> tuple[subprocess.CompletedProcess[str], Path, str, int]:
    script = _inside(root, end_to_end["script"])
    request = temporary_directory / "curl-request.json"
    request.write_text(
        json.dumps(
            {
                "arguments": [
                    "--disable",
                    "--request",
                    "HEAD",
                    "https://api.example.invalid/health",
                ],
                "intent": {"method": "HEAD"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    completed = _run(
        [sys.executable, str(script), "--input", str(request)],
        temporary_directory,
    )
    output = temporary_directory / "curl-request-e2e.json"
    output.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    payload = json.loads(completed.stdout)
    protections = payload["protections"]
    if protections["network_executed"] or protections["referenced_files_read"]:
        raise EvalError("curl request E2E crossed its read-only boundary")
    if not protections["input_bounded"] or not protections["values_redacted"]:
        raise EvalError("curl request E2E omitted an input or redaction gate")
    gate_count = len(protections) + len(payload["findings"])
    return completed, output, payload["status"], gate_count


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

    originality = value.get("originality")
    if originality is not None:
        if (
            not isinstance(originality, dict)
            or originality.get("result") != "distinct"
            or not isinstance(originality.get("compared_capabilities"), list)
            or not originality["compared_capabilities"]
            or not isinstance(originality.get("rationale"), str)
            or len(originality["rationale"].strip()) < 40
        ):
            raise EvalError("originality review needs representative comparisons and a distinct result")

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
    elif kind == "git-transfer-bundle":
        completed, output, result, gate_count = _git_transfer_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "ansible-collection-plan":
        completed, output, result, gate_count = _ansible_collection_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "npm-package-readiness":
        completed, output, result, gate_count = _npm_package_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "cargo-build-performance":
        completed, output, result, gate_count = _cargo_performance_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "cors-diagnosis":
        completed, output, result, gate_count = _cors_diagnosis_e2e(
            root, end_to_end, temporary_directory
        )
    elif kind == "curl-request-audit":
        completed, output, result, gate_count = _curl_request_e2e(
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
    minimum_gates = end_to_end.get("minimum_gates")
    if minimum_gates is not None and gate_count < minimum_gates:
        raise EvalError("end-to-end report omitted required gates")
    positive = sum(case["expected"] == "trigger" for case in cases)
    return {
        "capability_id": value["capability_id"],
        "trigger_cases": len(cases),
        "positive": positive,
        "negative": len(cases) - positive,
        "originality": originality["result"] if originality is not None else "not-recorded",
        "e2e_result": result,
        "e2e_gates": gate_count,
        "report_path": str(output),
    }
