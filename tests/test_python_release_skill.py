from __future__ import annotations

import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.evals import run_eval_file


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "python-package-delivery"
    / "skills"
    / "audit-python-release-readiness"
    / "scripts"
    / "inspect_dist.py"
)


def _tar_bytes(archive: tarfile.TarFile, name: str, data: bytes) -> None:
    member = tarfile.TarInfo(name)
    member.size = len(data)
    archive.addfile(member, io.BytesIO(data))


def create_fixture(root: Path, *, unsafe_wheel: bool = False) -> tuple[Path, Path, Path]:
    project = root / "project"
    dist = project / "dist"
    dist.mkdir(parents=True)
    pyproject = project / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "sample-pkg"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    sdist_root = "sample_pkg-1.2.3"
    with tarfile.open(dist / "sample_pkg-1.2.3.tar.gz", "w:gz") as archive:
        _tar_bytes(archive, f"{sdist_root}/pyproject.toml", pyproject.read_bytes())
        _tar_bytes(
            archive,
            f"{sdist_root}/PKG-INFO",
            b"Metadata-Version: 2.4\nName: sample-pkg\nVersion: 1.2.3\n",
        )
    dist_info = "sample_pkg-1.2.3.dist-info"
    wheel_entries = {
        "sample_pkg/__init__.py": b"__version__ = '1.2.3'\n",
        f"{dist_info}/METADATA": (
            b"Metadata-Version: 2.4\nName: sample-pkg\nVersion: "
            + (b"9.9.9" if unsafe_wheel else b"1.2.3")
            + b"\n"
        ),
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
    }
    if unsafe_wheel:
        wheel_entries["../escape.py"] = b"raise RuntimeError('must never run')\n"
    record_path = f"{dist_info}/RECORD"
    wheel_entries[record_path] = "".join(
        f"{name},,\n" for name in [*wheel_entries, record_path]
    ).encode()
    with zipfile.ZipFile(
        dist / "sample_pkg-1.2.3-py3-none-any.whl", "w"
    ) as archive:
        for name, data in wheel_entries.items():
            archive.writestr(name, data)
    workflow = project / "release.yml"
    workflow.write_text(
        """name: publish
jobs:
  build:
    steps:
      - run: python -m build
  publish:
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
""",
        encoding="utf-8",
    )
    return pyproject, dist, workflow


def run_checker(root: Path, *, unsafe_wheel: bool = False) -> subprocess.CompletedProcess[str]:
    pyproject, dist, workflow = create_fixture(root, unsafe_wheel=unsafe_wheel)
    output = root / "report.md"
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--pyproject",
            str(pyproject),
            "--dist",
            str(dist),
            "--workflow",
            str(workflow),
            "--output",
            str(output),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


class PythonReleaseSkillTests(unittest.TestCase):
    def test_valid_artifacts_and_oidc_workflow_are_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = run_checker(root)

            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = (root / "report.md").read_text(encoding="utf-8")
            self.assertTrue(report.startswith("# Python release readiness: ready"))
            self.assertIn("workflow:job-separation | pass", report)
            self.assertIn("wheel:sample_pkg-1.2.3-py3-none-any.whl:record | pass", report)

    def test_mismatched_unsafe_wheel_fails_without_extracting_or_running_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = run_checker(root, unsafe_wheel=True)

            self.assertEqual(completed.returncode, 1)
            report = (root / "report.md").read_text(encoding="utf-8")
            self.assertTrue(report.startswith("# Python release readiness: not-ready"))
            self.assertIn("unsafe members", report)
            self.assertIn("Version='9.9.9'", report)
            self.assertFalse((root / "escape.py").exists())

    def test_reviewed_triggers_and_e2e_fixture_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT,
                ROOT / "evals" / "audit-python-release-readiness.json",
                Path(directory),
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["positive"], 3)
        self.assertEqual(report["negative"], 4)
        self.assertEqual(report["e2e_result"], "ready")
        self.assertGreaterEqual(report["e2e_gates"], 14)


if __name__ == "__main__":
    unittest.main()
