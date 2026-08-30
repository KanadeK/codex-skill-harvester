#!/usr/bin/env python3
"""Classify a captured Fetch/CORS exchange without making network requests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit


MAX_INPUT_BYTES = 1_000_000
SIMPLE_METHODS = {"GET", "HEAD", "POST"}
SIMPLE_HEADERS = {"accept", "accept-language", "content-language", "content-type"}
SIMPLE_CONTENT_TYPES = {
    "application/x-www-form-urlencoded",
    "multipart/form-data",
    "text/plain",
}


class EvidenceError(ValueError):
    pass


def _object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    return value


def _headers(value: object, label: str) -> dict[str, str]:
    raw = _object(value, label)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in raw.items()):
        raise EvidenceError(f"{label} must map header names to strings")
    return {key.lower(): item.strip() for key, item in raw.items()}


def _origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise EvidenceError(f"invalid HTTP origin or URL: {value}")
    default = 80 if parsed.scheme == "http" else 443
    port = parsed.port
    suffix = "" if port in {None, default} else f":{port}"
    return f"{parsed.scheme}://{parsed.hostname.lower()}{suffix}"


def _allowed_origin(headers: dict[str, str], page_origin: str, credentials: str) -> list[str]:
    value = headers.get("access-control-allow-origin")
    if value is None:
        return ["access-control-allow-origin is missing"]
    if value == "*" and credentials == "include":
        return ["wildcard access-control-allow-origin cannot authorize credentials"]
    if value != "*" and value != page_origin:
        return ["access-control-allow-origin does not match the page origin"]
    if credentials == "include" and headers.get("access-control-allow-credentials", "").lower() != "true":
        return ["credentialed request lacks access-control-allow-credentials: true"]
    return []


def classify(value: object) -> dict[str, object]:
    evidence = _object(value, "evidence")
    page_origin_raw = evidence.get("page_origin")
    if not isinstance(page_origin_raw, str):
        raise EvidenceError("page_origin must be a string")
    page_origin = _origin(page_origin_raw)
    request = _object(evidence.get("request"), "request")
    request_url = request.get("url")
    if not isinstance(request_url, str):
        raise EvidenceError("request.url must be a string")
    request_origin = _origin(request_url)
    method = request.get("method", "GET")
    mode = request.get("mode", "cors")
    credentials = request.get("credentials", "same-origin")
    if not isinstance(method, str) or mode not in {"cors", "no-cors", "same-origin"}:
        raise EvidenceError("request method or mode is invalid")
    if credentials not in {"omit", "same-origin", "include"}:
        raise EvidenceError("request.credentials is invalid")
    request_headers = _headers(request.get("headers", {}), "request.headers")
    if page_origin == request_origin:
        return {"status": "same-origin", "phase": "none", "findings": [], "preflight_required": False}
    if mode == "same-origin":
        return {"status": "blocked", "phase": "request", "findings": ["same-origin mode blocks a cross-origin URL"], "preflight_required": False}
    if mode == "no-cors":
        return {"status": "opaque", "phase": "response", "findings": ["no-cors mode yields an opaque response and does not grant CORS access"], "preflight_required": False}

    content_type = request_headers.get("content-type", "").split(";", 1)[0].strip().lower()
    non_simple_headers = sorted(set(request_headers) - SIMPLE_HEADERS)
    if "content-type" in request_headers and content_type not in SIMPLE_CONTENT_TYPES:
        non_simple_headers.append("content-type")
    preflight_required = method.upper() not in SIMPLE_METHODS or bool(non_simple_headers)
    findings = []
    if preflight_required:
        raw_preflight = evidence.get("preflight")
        if raw_preflight is None:
            return {"status": "unverified", "phase": "preflight", "findings": ["preflight evidence is missing"], "preflight_required": True}
        preflight = _object(raw_preflight, "preflight")
        status = preflight.get("status")
        if not isinstance(status, int) or not 200 <= status < 300:
            findings.append("preflight status is not successful")
        preflight_headers = _headers(preflight.get("headers", {}), "preflight.headers")
        findings.extend(_allowed_origin(preflight_headers, page_origin, credentials))
        methods = {item.strip().upper() for item in preflight_headers.get("access-control-allow-methods", "").split(",") if item.strip()}
        if method.upper() not in methods:
            findings.append("access-control-allow-methods does not include the request method")
        allowed_headers = {item.strip().lower() for item in preflight_headers.get("access-control-allow-headers", "").split(",") if item.strip()}
        missing_headers = sorted(set(non_simple_headers) - allowed_headers)
        if missing_headers:
            findings.append("access-control-allow-headers omits: " + ", ".join(missing_headers))
        if findings:
            return {"status": "blocked", "phase": "preflight", "findings": findings, "preflight_required": True}

    response = _object(evidence.get("response"), "response")
    response_headers = _headers(response.get("headers", {}), "response.headers")
    findings.extend(_allowed_origin(response_headers, page_origin, credentials))
    return {
        "status": "blocked" if findings else "allowed",
        "phase": "response" if findings else "complete",
        "findings": findings,
        "preflight_required": preflight_required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_INPUT_BYTES:
            raise EvidenceError(f"input exceeds {MAX_INPUT_BYTES} bytes")
        value = json.loads(args.input.read_text(encoding="utf-8"))
        report = classify(value)
    except (OSError, UnicodeError, json.JSONDecodeError, EvidenceError) as error:
        print(json.dumps({"status": "invalid", "error": str(error)}), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] in {"allowed", "same-origin"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
