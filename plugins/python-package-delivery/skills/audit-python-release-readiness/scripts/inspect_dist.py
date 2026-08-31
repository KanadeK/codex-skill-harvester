from __future__ import annotations

import argparse
import csv
import io
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path, PurePosixPath


MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_DISTRIBUTION_FILES = 128
MAX_TOTAL_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_RECORD_BYTES = 8 * 1024 * 1024


def _archive_name(value: str) -> str:
    return re.sub(r"[-_.]+", "_", value).lower()


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return not path.is_absolute() and ".." not in path.parts


def _detail(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _check(
    checks: list[dict[str, str]], code: str, status: str, detail: object
) -> None:
    checks.append({"code": code, "status": status, "detail": _detail(detail)})


def _metadata_identity(data: bytes) -> tuple[str | None, str | None]:
    message = BytesParser(policy=default).parsebytes(data)
    return message.get("Name"), message.get("Version")


def _archive_size_allowed(
    path: Path, code: str, checks: list[dict[str, str]]
) -> bool:
    size = path.stat().st_size
    allowed = size <= MAX_ARCHIVE_BYTES
    _check(
        checks,
        f"{code}:archive-size",
        "pass" if allowed else "fail",
        f"bytes={size} limit={MAX_ARCHIVE_BYTES}",
    )
    return allowed


def _bounded_zip_read(
    archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int
) -> bytes | None:
    if info.file_size > limit:
        return None
    with archive.open(info) as extracted:
        data = extracted.read(limit + 1)
    return data if len(data) <= limit else None


def _inspect_sdist(
    path: Path,
    *,
    expected_name: str,
    expected_version: str,
    checks: list[dict[str, str]],
) -> None:
    code = f"sdist:{path.name}"
    expected_filename = f"{expected_name}-{expected_version}.tar.gz"
    _check(
        checks,
        f"{code}:filename",
        "pass" if path.name == expected_filename else "fail",
        f"expected {expected_filename}",
    )
    try:
        if not _archive_size_allowed(path, code, checks):
            return
        with tarfile.open(path, mode="r:gz") as archive:
            members: list[tarfile.TarInfo] = []
            expanded_bytes = 0
            for member in archive:
                if len(members) >= MAX_ARCHIVE_MEMBERS:
                    _check(
                        checks,
                        f"{code}:member-count",
                        "fail",
                        f"members exceed limit={MAX_ARCHIVE_MEMBERS}",
                    )
                    return
                expanded_bytes += member.size
                if expanded_bytes > MAX_EXPANDED_BYTES:
                    _check(
                        checks,
                        f"{code}:expanded-size",
                        "fail",
                        f"declared bytes exceed limit={MAX_EXPANDED_BYTES}",
                    )
                    return
                members.append(member)
            _check(
                checks,
                f"{code}:member-count",
                "pass",
                f"members={len(members)} limit={MAX_ARCHIVE_MEMBERS}",
            )
            _check(
                checks,
                f"{code}:expanded-size",
                "pass",
                f"declared_bytes={expanded_bytes} limit={MAX_EXPANDED_BYTES}",
            )
            unsafe = [member.name for member in members if not _safe_member(member.name)]
            _check(
                checks,
                f"{code}:paths",
                "pass" if not unsafe else "fail",
                "all member paths stay inside the archive root"
                if not unsafe
                else f"unsafe members: {', '.join(unsafe[:5])}",
            )
            roots = {PurePosixPath(member.name).parts[0] for member in members if member.name}
            expected_root = f"{expected_name}-{expected_version}"
            _check(
                checks,
                f"{code}:root",
                "pass" if roots == {expected_root} else "fail",
                f"roots={sorted(roots)} expected={expected_root}",
            )
            by_name = {member.name: member for member in members}
            pyproject_name = f"{expected_root}/pyproject.toml"
            pkg_info_name = f"{expected_root}/PKG-INFO"
            missing = [
                name for name in (pyproject_name, pkg_info_name) if name not in by_name
            ]
            _check(
                checks,
                f"{code}:required-files",
                "pass" if not missing else "fail",
                "pyproject.toml and PKG-INFO present"
                if not missing
                else f"missing {', '.join(missing)}",
            )
            if pkg_info_name in by_name:
                metadata_member = by_name[pkg_info_name]
                if metadata_member.size > MAX_METADATA_BYTES:
                    _check(
                        checks,
                        f"{code}:metadata-size",
                        "fail",
                        f"bytes={metadata_member.size} limit={MAX_METADATA_BYTES}",
                    )
                else:
                    _check(
                        checks,
                        f"{code}:metadata-size",
                        "pass",
                        f"bytes={metadata_member.size} limit={MAX_METADATA_BYTES}",
                    )
                    extracted = archive.extractfile(metadata_member)
                    if extracted is None:
                        _check(checks, f"{code}:metadata", "fail", "PKG-INFO is unreadable")
                    else:
                        data = extracted.read(MAX_METADATA_BYTES + 1)
                        if len(data) > MAX_METADATA_BYTES:
                            _check(
                                checks,
                                f"{code}:metadata-size",
                                "fail",
                                f"read exceeds limit={MAX_METADATA_BYTES}",
                            )
                        else:
                            name, version = _metadata_identity(data)
                            matches = (
                                _archive_name(name or "") == expected_name
                                and version == expected_version
                            )
                            _check(
                                checks,
                                f"{code}:metadata",
                                "pass" if matches else "fail",
                                f"Name={name!r} Version={version!r}",
                            )
    except (OSError, tarfile.TarError) as error:
        _check(checks, f"{code}:archive", "fail", f"unreadable sdist: {error}")


def _inspect_wheel(
    path: Path,
    *,
    expected_name: str,
    expected_version: str,
    checks: list[dict[str, str]],
) -> None:
    code = f"wheel:{path.name}"
    expected_prefix = f"{expected_name}-{expected_version}-"
    _check(
        checks,
        f"{code}:filename",
        "pass" if path.name.startswith(expected_prefix) else "fail",
        f"expected prefix {expected_prefix}",
    )
    try:
        if not _archive_size_allowed(path, code, checks):
            return
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                _check(
                    checks,
                    f"{code}:member-count",
                    "fail",
                    f"members={len(infos)} limit={MAX_ARCHIVE_MEMBERS}",
                )
                return
            _check(
                checks,
                f"{code}:member-count",
                "pass",
                f"members={len(infos)} limit={MAX_ARCHIVE_MEMBERS}",
            )
            expanded_bytes = sum(info.file_size for info in infos)
            if expanded_bytes > MAX_EXPANDED_BYTES:
                _check(
                    checks,
                    f"{code}:expanded-size",
                    "fail",
                    f"declared_bytes={expanded_bytes} limit={MAX_EXPANDED_BYTES}",
                )
                return
            _check(
                checks,
                f"{code}:expanded-size",
                "pass",
                f"declared_bytes={expanded_bytes} limit={MAX_EXPANDED_BYTES}",
            )
            names = [info.filename for info in infos]
            by_name = {info.filename: info for info in infos}
            unsafe = [name for name in names if not _safe_member(name)]
            _check(
                checks,
                f"{code}:paths",
                "pass" if not unsafe else "fail",
                "all member paths are relative"
                if not unsafe
                else f"unsafe members: {', '.join(unsafe[:5])}",
            )
            expected_dist_info = f"{expected_name}-{expected_version}.dist-info"
            metadata_path = f"{expected_dist_info}/METADATA"
            wheel_path = f"{expected_dist_info}/WHEEL"
            record_path = f"{expected_dist_info}/RECORD"
            missing = [
                name for name in (metadata_path, wheel_path, record_path) if name not in names
            ]
            _check(
                checks,
                f"{code}:required-files",
                "pass" if not missing else "fail",
                "METADATA, WHEEL, and RECORD present"
                if not missing
                else f"missing {', '.join(missing)}",
            )
            if metadata_path in names:
                metadata = _bounded_zip_read(
                    archive, by_name[metadata_path], MAX_METADATA_BYTES
                )
                _check(
                    checks,
                    f"{code}:metadata-size",
                    "pass" if metadata is not None else "fail",
                    f"bytes={by_name[metadata_path].file_size} limit={MAX_METADATA_BYTES}",
                )
                if metadata is not None:
                    name, version = _metadata_identity(metadata)
                    matches = (
                        _archive_name(name or "") == expected_name
                        and version == expected_version
                    )
                    _check(
                        checks,
                        f"{code}:metadata",
                        "pass" if matches else "fail",
                        f"Name={name!r} Version={version!r}",
                    )
            if record_path in names:
                record = _bounded_zip_read(
                    archive, by_name[record_path], MAX_RECORD_BYTES
                )
                _check(
                    checks,
                    f"{code}:record-size",
                    "pass" if record is not None else "fail",
                    f"bytes={by_name[record_path].file_size} limit={MAX_RECORD_BYTES}",
                )
                if record is not None:
                    rows = csv.reader(io.StringIO(record.decode("utf-8")))
                    recorded = {row[0] for row in rows if row}
                    unrecorded = [
                        name
                        for name in names
                        if name not in recorded
                        and not name.endswith(("RECORD.jws", "RECORD.p7s"))
                    ]
                    _check(
                        checks,
                        f"{code}:record",
                        "pass" if not unrecorded else "fail",
                        "all wheel members appear in RECORD"
                        if not unrecorded
                        else f"unrecorded members: {', '.join(unrecorded[:5])}",
                    )
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        _check(checks, f"{code}:archive", "fail", f"unreadable wheel: {error}")


def _workflow_jobs(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", text))
    return {
        match.group(1): text[match.start() : matches[index + 1].start()]
        if index + 1 < len(matches)
        else text[match.start() :]
        for index, match in enumerate(matches)
    }


def _job_has_oidc_write(block: str) -> bool:
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not re.fullmatch(r" {4}permissions:\s*(?:#.*)?", line):
            continue
        for nested in lines[index + 1 :]:
            if not nested.strip() or nested.lstrip().startswith("#"):
                continue
            indentation = len(nested) - len(nested.lstrip(" "))
            if indentation <= 4:
                break
            if re.fullmatch(
                r''' {6}(?:id-token|'id-token'|"id-token"):\s*'''
                r'''(?:write|'write'|"write")\s*(?:#.*)?''',
                nested,
            ):
                return True
    return False


def _inspect_workflow(path: Path, checks: list[dict[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    jobs = _workflow_jobs(text)
    build_jobs = {
        name for name, block in jobs.items() if re.search(r"python\s+-m\s+build", block)
    }
    publish_jobs = {
        name
        for name, block in jobs.items()
        if "pypa/gh-action-pypi-publish@" in block
    }
    _check(
        checks,
        "workflow:job-separation",
        "pass" if build_jobs and publish_jobs and build_jobs.isdisjoint(publish_jobs) else "fail",
        f"build_jobs={sorted(build_jobs)} publish_jobs={sorted(publish_jobs)}",
    )
    publish_blocks = "\n".join(jobs[name] for name in publish_jobs)
    _check(
        checks,
        "workflow:oidc-permission",
        "pass" if any(_job_has_oidc_write(jobs[name]) for name in publish_jobs) else "fail",
        "id-token: write is scoped inside a publishing job",
    )
    secret_pattern = re.compile(r"PYPI_API_TOKEN|password\s*:", re.IGNORECASE)
    _check(
        checks,
        "workflow:long-lived-secret",
        "fail" if secret_pattern.search(text) else "pass",
        "no PyPI token or password marker found"
        if not secret_pattern.search(text)
        else "long-lived credential marker found",
    )
    action = re.search(r"pypa/gh-action-pypi-publish@([^\s#]+)", text)
    accepted = action and (
        action.group(1) == "release/v1" or re.fullmatch(r"[0-9a-f]{40}", action.group(1))
    )
    _check(
        checks,
        "workflow:publish-action-ref",
        "pass" if accepted else "warn",
        f"action ref={action.group(1) if action else None!r}",
    )
    _check(
        checks,
        "workflow:environment",
        "pass" if re.search(r"(?m)^\s+environment:\s*\S+", publish_blocks) else "warn",
        "publishing environment declared"
        if "environment:" in publish_blocks
        else "manual review: no publishing environment marker",
    )


def inspect(pyproject: Path, dist: Path, workflow: Path | None) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    try:
        configuration = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        _check(checks, "project:pyproject", "fail", f"unreadable pyproject.toml: {error}")
        return checks
    project = configuration.get("project")
    if not isinstance(project, dict):
        _check(checks, "project:metadata", "fail", "missing [project] table")
        return checks
    name = project.get("name")
    version = project.get("version")
    if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
        _check(
            checks,
            "project:identity",
            "fail",
            "static project.name and project.version are required for deterministic comparison",
        )
        return checks
    _check(checks, "project:identity", "pass", f"Name={name!r} Version={version!r}")
    normalized_name = _archive_name(name)
    sdists = sorted(dist.glob("*.tar.gz"))
    wheels = sorted(dist.glob("*.whl"))
    _check(checks, "artifacts:sdist-present", "pass" if sdists else "fail", f"sdists={len(sdists)}")
    _check(checks, "artifacts:wheel-present", "pass" if wheels else "fail", f"wheels={len(wheels)}")
    artifacts = [*sdists, *wheels]
    file_count_allowed = len(artifacts) <= MAX_DISTRIBUTION_FILES
    _check(
        checks,
        "artifacts:file-count",
        "pass" if file_count_allowed else "fail",
        f"files={len(artifacts)} limit={MAX_DISTRIBUTION_FILES}",
    )
    if not file_count_allowed:
        return checks
    try:
        total_archive_bytes = sum(path.stat().st_size for path in artifacts)
    except OSError as error:
        _check(checks, "artifacts:total-bytes", "fail", f"unreadable artifact: {error}")
        return checks
    total_bytes_allowed = total_archive_bytes <= MAX_TOTAL_ARCHIVE_BYTES
    _check(
        checks,
        "artifacts:total-bytes",
        "pass" if total_bytes_allowed else "fail",
        f"bytes={total_archive_bytes} limit={MAX_TOTAL_ARCHIVE_BYTES}",
    )
    if not total_bytes_allowed:
        return checks
    for path in sdists:
        _inspect_sdist(path, expected_name=normalized_name, expected_version=version, checks=checks)
    for path in wheels:
        _inspect_wheel(path, expected_name=normalized_name, expected_version=version, checks=checks)
    if workflow is None:
        _check(checks, "workflow:provided", "warn", "no publishing workflow was supplied")
    else:
        try:
            _inspect_workflow(workflow, checks)
        except (OSError, UnicodeDecodeError) as error:
            _check(checks, "workflow:read", "fail", f"unreadable workflow: {error}")
    return checks


def _render(checks: list[dict[str, str]]) -> str:
    failures = sum(check["status"] == "fail" for check in checks)
    warnings = sum(check["status"] == "warn" for check in checks)
    result = "ready" if failures == 0 else "not-ready"
    lines = [
        f"# Python release readiness: {result}",
        "",
        f"- Failed gates: {failures}",
        f"- Warnings: {warnings}",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| {check['code']} | {check['status']} | {check['detail']} |"
        for check in checks
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect Python distributions without extracting or publishing them."
    )
    parser.add_argument("--pyproject", type=Path, required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--workflow", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checks = inspect(args.pyproject, args.dist, args.workflow)
    args.output.write_text(_render(checks), encoding="utf-8")
    return 1 if any(check["status"] == "fail" for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
