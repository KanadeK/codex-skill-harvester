from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    parser = argparse.ArgumentParser(description="install and invoke a built release archive")
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "dist" / f"codex-skill-harvester-v{version}.zip",
    )
    archive = parser.parse_args(argv).archive.resolve()
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                destination = (temporary / member.filename).resolve()
                if not destination.is_relative_to(temporary.resolve()):
                    raise ValueError(f"archive member escapes extraction root: {member.filename}")
            package.extractall(temporary)
        extracted = temporary / f"codex-skill-harvester-{version}"
        target = temporary / "site-packages"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                "--no-deps",
                "--target",
                str(target),
                str(extracted),
            ],
            check=True,
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(target)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        invocation = subprocess.run(
            [sys.executable, "-m", "skill_harvester", "--help"],
            cwd=temporary,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        if "Incrementally scan registered public workflow evidence" not in invocation.stdout:
            raise ValueError("installed CLI help did not contain the expected command description")
        subprocess.run(
            [sys.executable, str(extracted / "scripts" / "validate_repo.py")],
            cwd=extracted,
            env=environment,
            check=True,
        )
    print("release_archive_install_and_call=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
