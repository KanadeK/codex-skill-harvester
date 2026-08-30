#!/usr/bin/env python3
"""Audit a normalized curl request without executing curl or reading referenced files."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path
from urllib.parse import urlsplit


MAX_INPUT_BYTES = 1_000_000
MAX_ARGUMENTS = 2_000
MAX_ARGUMENT_BYTES = 100_000
MAX_CONFIG_BYTES = 1_000_000
MAX_CONFIG_LINES = 20_000
VALUE_OPTIONS = {
    "--config",
    "--data",
    "--data-binary",
    "--data-raw",
    "--data-urlencode",
    "--form",
    "--header",
    "--oauth2-bearer",
    "--request",
    "--url",
    "--user",
}
ALIASES = {
    "-K": "--config",
    "-d": "--data",
    "-F": "--form",
    "-G": "--get",
    "-H": "--header",
    "-I": "--head",
    "-q": "--disable",
    "-u": "--user",
    "-X": "--request",
}
SHORT_VALUE_OPTIONS = {key for key, value in ALIASES.items() if value in VALUE_OPTIONS}
DATA_OPTIONS = {"--data", "--data-binary", "--data-raw", "--data-urlencode", "--form"}
CREDENTIAL_OPTIONS = {"--oauth2-bearer", "--user"}
METHOD = re.compile(r"[A-Z]+")
CONFIG_LINE = re.compile(
    r"^(?P<option>-{0,2}[A-Za-z0-9][A-Za-z0-9_-]*)(?:(?:\s*[:=]\s*|\s+)(?P<value>.*))?$"
)


class AuditError(ValueError):
    pass


def _bounded_text(path: Path, limit: int, label: str) -> str:
    if not path.is_file():
        raise AuditError(f"{label} must be an existing file")
    if path.stat().st_size > limit:
        raise AuditError(f"{label} exceeds {limit} bytes")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as error:
        raise AuditError(f"{label} must be UTF-8: {error}") from error


def _input(path: Path) -> tuple[list[str], str | None]:
    try:
        value = json.loads(_bounded_text(path, MAX_INPUT_BYTES, "input JSON"))
    except json.JSONDecodeError as error:
        raise AuditError(f"input is not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AuditError("input JSON must be an object")
    arguments = value.get("arguments")
    if (
        not isinstance(arguments, list)
        or len(arguments) > MAX_ARGUMENTS
        or any(not isinstance(item, str) for item in arguments)
    ):
        raise AuditError(f"arguments must contain at most {MAX_ARGUMENTS} strings")
    if any(len(item.encode("utf-8")) > MAX_ARGUMENT_BYTES for item in arguments):
        raise AuditError(f"an argument exceeds {MAX_ARGUMENT_BYTES} bytes")
    intent = value.get("intent", {})
    if not isinstance(intent, dict):
        raise AuditError("intent must be an object")
    intended_method = intent.get("method")
    if intended_method is not None and not isinstance(intended_method, str):
        raise AuditError("intent.method must be a string")
    return arguments, intended_method.upper() if intended_method else None


def _config_value(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return ""
    if value.startswith('"'):
        try:
            parts = shlex.split(value, posix=True)
        except ValueError as error:
            raise AuditError(f"curl config contains invalid quoting: {error}") from error
        if len(parts) != 1:
            raise AuditError("curl config values must resolve to one argument")
        return parts[0]
    return value


def _config_entries(path: Path | None) -> list[tuple[str, str | None]]:
    if path is None:
        return []
    text = _bounded_text(path, MAX_CONFIG_BYTES, "curl config")
    lines = text.splitlines()
    if len(lines) > MAX_CONFIG_LINES:
        raise AuditError(f"curl config exceeds {MAX_CONFIG_LINES} lines")
    entries: list[tuple[str, str | None]] = []
    for number, raw_line in enumerate(lines, start=1):
        if len(raw_line.encode("utf-8")) > MAX_ARGUMENT_BYTES:
            raise AuditError(f"curl config line {number} exceeds {MAX_ARGUMENT_BYTES} bytes")
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        matched = CONFIG_LINE.fullmatch(line)
        if matched is None:
            raise AuditError(f"curl config line {number} has unsupported syntax")
        option = matched.group("option")
        if not option.startswith("-"):
            option = "--" + option
        option = ALIASES.get(option, option)
        entries.append((option, _config_value(matched.group("value"))))
    return entries


def _argument_entries(arguments: list[str]) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    index = 0
    positional = False
    while index < len(arguments):
        argument = arguments[index]
        if positional:
            entries.append(("url", argument))
            index += 1
            continue
        if argument == "--":
            positional = True
            index += 1
            continue
        if not argument.startswith("-") or argument == "-":
            entries.append(("url", argument))
            index += 1
            continue

        option = argument
        value: str | None = None
        if argument.startswith("--") and "=" in argument:
            option, value = argument.split("=", 1)
        elif argument[:2] in SHORT_VALUE_OPTIONS and len(argument) > 2:
            option, value = argument[:2], argument[2:]
        option = ALIASES.get(option, option)
        if option in VALUE_OPTIONS and value is None:
            index += 1
            if index >= len(arguments):
                raise AuditError(f"{option} is missing its value")
            value = arguments[index]
        entries.append((option, value))
        index += 1
    return entries


def _is_file_reference(option: str, value: str | None) -> bool:
    if value is None or option == "--data-raw":
        return False
    if option in {"--data", "--data-binary", "--form"}:
        return value.startswith("@") or "=@" in value
    if option == "--data-urlencode":
        return value.startswith("@") or ("=" not in value and "@" in value)
    return False


def inspect(arguments: list[str], intended_method: str | None, config: Path | None) -> dict[str, object]:
    config_entries = _config_entries(config)
    argument_entries = _argument_entries(arguments)
    entries = [*config_entries, *argument_entries]
    findings: list[dict[str, str]] = []

    def add(code: str, severity: str, message: str) -> None:
        findings.append({"code": code, "severity": severity, "message": message})

    default_disabled = bool(arguments) and arguments[0] in {"-q", "--disable"}
    if not default_disabled:
        add(
            "implicit-default-config",
            "warning",
            "curl may load a default config before the reviewed arguments; put --disable first to make the audit complete",
        )

    urls = [value for option, value in entries if option in {"url", "--url"} and value]
    if not urls:
        add("missing-url", "warning", "the reviewed request does not contain a URL")
    elif len(urls) > 1:
        add("multiple-urls", "block", "this single-request audit does not cover multiple transfer URLs")

    requests = [value for option, value in entries if option == "--request" and value]
    requested_method = requests[-1].upper() if requests else None
    if requested_method is not None and METHOD.fullmatch(requested_method) is None:
        add("invalid-method-token", "block", "the custom request method is not a plain HTTP method token")
        requested_method = None
    head_mode = any(option == "--head" for option, _ in entries)
    get_mode = any(option == "--get" for option, _ in entries)
    body_entries = [(option, value) for option, value in entries if option in DATA_OPTIONS]
    inferred_method = (
        "HEAD"
        if head_mode
        else "GET"
        if get_mode
        else requested_method
        if requested_method is not None
        else "POST"
        if body_entries
        else "GET"
    )
    if requested_method == "HEAD" and not head_mode:
        add(
            "request-head-without-head-mode",
            "block",
            "--request HEAD changes only the method token; use curl head mode when HEAD behavior is intended",
        )
    if intended_method is not None:
        if METHOD.fullmatch(intended_method) is None:
            raise AuditError("intent.method must be a plain HTTP method token")
        if intended_method != inferred_method:
            add(
                "intent-method-mismatch",
                "block",
                "the inferred curl method does not match the declared request intent",
            )

    file_reference_options = sorted(
        {
            option
            for option, value in body_entries
            if _is_file_reference(option, value)
        }
    )
    if file_reference_options:
        add(
            "unread-file-reference",
            "block",
            "one or more body options reference local files that this bounded audit deliberately did not read",
        )

    credential_options = {
        option for option, _ in entries if option in CREDENTIAL_OPTIONS
    }
    for option, value in entries:
        if option == "--header" and value is not None:
            header_name = value.split(":", 1)[0].strip().lower()
            if header_name in {"authorization", "cookie", "proxy-authorization"}:
                credential_options.add("--header")
    url_schemes = []
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme:
            url_schemes.append(parsed.scheme.lower())
        if parsed.username is not None or parsed.password is not None:
            credential_options.add("url-userinfo")
    if credential_options:
        add(
            "credential-bearing-request",
            "block",
            "credential-bearing options require a separately approved secret-handling workflow",
        )

    config_references = sum(option == "--config" for option, _ in argument_entries)
    uninspected_configs = max(0, config_references - (1 if config is not None else 0))
    if uninspected_configs:
        add(
            "uninspected-config-reference",
            "block",
            "the argument list references a curl config; pass its reviewed path with --config",
        )

    status = (
        "blocked"
        if any(item["severity"] == "block" for item in findings)
        else "unverified"
        if findings
        else "reviewable"
    )
    return {
        "status": status,
        "request": {
            "method": inferred_method,
            "url_count": len(urls),
            "url_schemes": sorted(set(url_schemes)),
            "body_options": sorted({option for option, _ in body_entries}),
            "file_reference_options": file_reference_options,
            "credential_options": sorted(credential_options),
            "explicit_config_inspected": config is not None,
        },
        "findings": findings,
        "protections": {
            "input_bounded": True,
            "network_executed": False,
            "referenced_files_read": False,
            "values_redacted": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        arguments, intended_method = _input(args.input)
        report = inspect(arguments, intended_method, args.config)
    except AuditError as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "reviewable" else 1


if __name__ == "__main__":
    raise SystemExit(main())
