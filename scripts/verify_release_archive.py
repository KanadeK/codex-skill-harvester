from __future__ import annotations

import argparse
import json
import os
import shutil
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
        sys.path.insert(0, str(target))
        from skill_harvester.evals import run_eval_file

        marketplace = json.loads(
            (extracted / ".agents" / "plugins" / "marketplace.json").read_text(
                encoding="utf-8"
            )
        )
        plugin_eval_root = temporary / "plugin-eval"
        (plugin_eval_root / "plugins").mkdir(parents=True)
        shutil.copytree(extracted / "evals", plugin_eval_root / "evals")
        for entry in marketplace["plugins"]:
            plugin_id = entry["name"]
            plugin_archive = archive.parent / f"{plugin_id}-v{version}.zip"
            plugin_extract = temporary / f"extract-{plugin_id}"
            plugin_extract.mkdir()
            with zipfile.ZipFile(plugin_archive) as package:
                for member in package.infolist():
                    destination = (plugin_extract / member.filename).resolve()
                    if not destination.is_relative_to(plugin_extract.resolve()):
                        raise ValueError(
                            f"plugin archive member escapes extraction root: {member.filename}"
                        )
                package.extractall(plugin_extract)
            isolated_plugin = plugin_extract / plugin_id
            manifest = json.loads(
                (isolated_plugin / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            if manifest["name"] != plugin_id or manifest["skills"] != "./skills/":
                raise ValueError(f"isolated plugin manifest is invalid: {plugin_id}")
            shutil.copytree(
                isolated_plugin, plugin_eval_root / "plugins" / plugin_id
            )
        for eval_path in sorted((plugin_eval_root / "evals").glob("*.json")):
            run_eval_file(plugin_eval_root, eval_path, temporary)
    print("release_archive_install_and_call=PASS")
    print("plugin_archives_install_and_e2e=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
