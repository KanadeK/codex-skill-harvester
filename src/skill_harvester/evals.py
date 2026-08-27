from __future__ import annotations

import os
import subprocess
import sys
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

    plugin_id, skill_name = value["capability_id"].split(":", 1)
    script = root / "plugins" / plugin_id / "skills" / skill_name / "scripts" / "check_snapshot.py"
    end_to_end = value["end_to_end"]
    snapshot = _inside(root, end_to_end["snapshot"])
    output = temporary_directory / "release-audit.md"
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(script), str(snapshot), "--output", str(output)],
        cwd=temporary_directory,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != end_to_end["expected_exit_code"]:
        raise EvalError(
            f"end-to-end script exited {completed.returncode}: {completed.stderr.strip()}"
        )
    markdown = output.read_text(encoding="utf-8")
    result = markdown.splitlines()[0].removeprefix("# Release audit: ")
    gate_count = sum(
        line.startswith("| ")
        and not line.startswith("| Gate ")
        and not line.startswith("| --- ")
        for line in markdown.splitlines()
    )
    if result != end_to_end["expected_result"] or gate_count != end_to_end["expected_gates"]:
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
