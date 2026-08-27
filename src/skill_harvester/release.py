from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

from .validation import ValidationError, validate_repository


EXCLUDED_PARTS = {".git", "dist", "build", ".venv", "__pycache__", ".harvester-cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".pem", ".key"}
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


def _version(root: Path) -> str:
    match = re.search(
        r'(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"\s*$',
        (root / "pyproject.toml").read_text(encoding="utf-8"),
    )
    if not match:
        raise ValidationError("pyproject.toml has no strict semantic version")
    return match.group(1)


def _files(root: Path, base: Path) -> list[Path]:
    files: list[Path] = []
    for path in base.rglob("*"):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValidationError(f"release input contains a symlink: {relative.as_posix()}")
        if path.is_file() and path.suffix not in EXCLUDED_SUFFIXES and not path.name.startswith(".env"):
            files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def _portable_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if b"\0" in data:
        return data
    text = data.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _write_zip(path: Path, entries: list[tuple[str, Path]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for archive_name, source in entries:
            info = zipfile.ZipInfo(archive_name, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, _portable_bytes(source))


def build_release(root: Path, output_directory: Path) -> list[Path]:
    root = root.resolve()
    validate_repository(root)
    version = _version(root)
    output_directory.mkdir(parents=True, exist_ok=True)
    source_archive = output_directory / f"codex-skill-harvester-v{version}.zip"
    plugin_archive = output_directory / f"github-release-evidence-v{version}.zip"

    repository_entries = [
        (f"codex-skill-harvester-{version}/{path.relative_to(root).as_posix()}", path)
        for path in _files(root, root)
    ]
    plugin_root = root / "plugins" / "github-release-evidence"
    plugin_entries = [
        (f"github-release-evidence/{path.relative_to(plugin_root).as_posix()}", path)
        for path in _files(root, plugin_root)
    ]
    _write_zip(source_archive, repository_entries)
    _write_zip(plugin_archive, plugin_entries)

    checksums = output_directory / "SHA256SUMS.txt"
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in (source_archive, plugin_archive)
    ]
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return [source_archive, plugin_archive, checksums]
