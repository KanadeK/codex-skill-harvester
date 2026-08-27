from __future__ import annotations

import json
import os
import re
import subprocess
import xml.etree.ElementTree as ElementTree
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .io import (
    atomic_write_json,
    atomic_write_text,
    canonical_json_bytes,
    load_json,
    sha256_bytes,
)


class RegistryError(ValueError):
    pass


class SourceFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class FetchResponse:
    status: int
    final_url: str
    headers: dict[str, str]
    body: bytes


class Fetcher(Protocol):
    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse: ...


class UrllibFetcher:
    def __init__(
        self,
        *,
        max_bytes: int = 2_000_000,
        timeout: float = 20.0,
        github_token: str | None = None,
    ) -> None:
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.github_token = github_token if github_token is not None else os.environ.get("GITHUB_TOKEN")

    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        if urlparse(url).scheme != "https":
            raise SourceFetchError("network sources must use https")
        request_headers = {
            "User-Agent": "codex-skill-harvester/0.1 (+https://github.com/KanadeK/codex-skill-harvester)",
            **headers,
        }
        request = Request(url, headers=request_headers)
        if urlparse(url).hostname == "api.github.com" and self.github_token:
            request.add_unredirected_header("Authorization", f"Bearer {self.github_token}")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                final_url = response.geturl()
                if urlparse(final_url).scheme != "https":
                    raise SourceFetchError("source redirected outside https")
                body = response.read(self.max_bytes + 1)
                if len(body) > self.max_bytes:
                    raise SourceFetchError(f"source response exceeded {self.max_bytes}-byte size limit")
                normalized_headers = {key.lower(): value for key, value in response.headers.items()}
                return FetchResponse(response.status, final_url, normalized_headers, body)
        except HTTPError as error:
            normalized_headers = {key.lower(): value for key, value in error.headers.items()}
            if error.code == 304:
                return FetchResponse(304, error.geturl(), normalized_headers, b"")
            raise SourceFetchError(f"source returned HTTP {error.code}") from error
        except URLError as error:
            raise SourceFetchError(f"source request failed: {error.reason}") from error


class GitHubCliFetcher:
    def __init__(
        self,
        *,
        delegate: Fetcher | None = None,
        executable: str = "gh",
        max_response_bytes: int = 2_000_000,
        timeout: float = 20.0,
    ) -> None:
        self.delegate = delegate or UrllibFetcher(github_token="")
        self.executable = executable
        self.max_response_bytes = max_response_bytes
        self.timeout = timeout

    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        parsed = urlparse(url)
        if parsed.hostname != "api.github.com":
            return self.delegate.fetch(url, headers)
        if parsed.scheme != "https":
            raise SourceFetchError("GitHub CLI sources must use https")
        endpoint = parsed.path.lstrip("/")
        if parsed.query:
            endpoint += f"?{parsed.query}"
        command = [self.executable, "api", "--method", "GET", endpoint]
        if headers.get("Accept"):
            command.extend(["-H", f"Accept: {headers['Accept']}"])
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise SourceFetchError(f"gh api request timed out after {self.timeout} seconds") from error
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace").strip()
            raise SourceFetchError(f"gh api request failed: {message}")
        if len(completed.stdout) > self.max_response_bytes:
            raise SourceFetchError(
                f"source response exceeded {self.max_response_bytes}-byte size limit"
            )
        return FetchResponse(200, url, {}, completed.stdout)


def load_registry(root: Path) -> list[dict[str, Any]]:
    registry = load_json(root / "sources" / "registry.json")
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        raise RegistryError("source registry must use schema_version 1")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RegistryError("source registry must contain at least one source")
    seen_ids: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise RegistryError("each source must be an object")
        source_id = source.get("id")
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
            raise RegistryError("source id must use lower-case kebab-case")
        if source_id in seen_ids:
            raise RegistryError(f"duplicate source id: {source_id}")
        seen_ids.add(source_id)
        url = source.get("url")
        if not isinstance(url, str) or urlparse(url).scheme != "https":
            raise RegistryError(f"source {source_id} must use an https URL")
        if source.get("adapter") not in {"document", "json-list", "atom"}:
            raise RegistryError(f"source {source_id} has an unsupported adapter")
        if source.get("trust") not in {"official", "representative", "discovery"}:
            raise RegistryError(f"source {source_id} has an unsupported trust tier")
        authentication = source.get("authentication")
        if authentication is not None and (
            authentication
            != {"type": "github", "methods": ["GITHUB_TOKEN", "gh-cli"]}
            or urlparse(url).hostname != "api.github.com"
        ):
            raise RegistryError(f"source {source_id} has unsupported authentication metadata")
        license_value = source.get("license")
        if not isinstance(license_value, dict) or license_value.get("status") not in {
            "known",
            "facts-only",
            "unknown",
        }:
            raise RegistryError(f"source {source_id} must declare license status")
    return sources


def _request_headers(previous: dict[str, Any]) -> dict[str, str]:
    headers = {"Accept": "application/json, application/atom+xml, text/plain, text/html"}
    if previous.get("etag"):
        headers["If-None-Match"] = previous["etag"]
    if previous.get("last_modified"):
        headers["If-Modified-Since"] = previous["last_modified"]
    return headers


def _document_discovery(
    source: dict[str, Any], response: FetchResponse, evidence_hash: str, now: str
) -> dict[str, Any]:
    text = response.body.decode("utf-8", errors="replace")
    headings = [match.group(1).strip() for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", text)]
    title = headings[0] if headings else source["id"]
    discovery_id = sha256_bytes(f"{source['id']}:{evidence_hash}".encode())[:24]
    revision = response.headers.get("etag") or response.headers.get("last-modified") or evidence_hash
    return {
        "schema_version": 1,
        "id": discovery_id,
        "source_id": source["id"],
        "source_revision": revision,
        "observed_at": now,
        "title": title,
        "canonical_url": response.final_url,
        "evidence_sha256": evidence_hash,
        "trust": source["trust"],
        "authority": source["authority"],
        "license": source["license"],
        "extracted_facts": [{"kind": "heading", "value": heading} for heading in headings[:20]],
        "review_status": "pending",
    }


def _item_discovery(
    source: dict[str, Any], item: dict[str, Any], item_hash: str, now: str
) -> dict[str, Any]:
    discovery_id = sha256_bytes(f"{source['id']}:{item['id']}:{item_hash}".encode())[:24]
    return {
        "schema_version": 1,
        "id": discovery_id,
        "source_id": source["id"],
        "source_item_id": item["id"],
        "source_revision": item["revision"],
        "observed_at": now,
        "title": item["title"],
        "canonical_url": item["url"],
        "evidence_sha256": item_hash,
        "trust": source["trust"],
        "authority": source["authority"],
        "license": source["license"],
        "extracted_facts": [
            {"kind": "source_revision", "value": item["revision"]},
            {"kind": "source_title", "value": item["title"]},
        ],
        "review_status": "pending",
    }


def _value_at_path(value: Any, path: str) -> Any:
    current = value
    if path:
        for component in path.split("."):
            if not isinstance(current, dict) or component not in current:
                raise SourceFetchError(f"JSON response is missing configured path: {path}")
            current = current[component]
    return current


def _json_items(source: dict[str, Any], body: bytes) -> list[dict[str, str]]:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceFetchError(f"source {source['id']} returned invalid JSON") from error
    extract = source.get("extract")
    if not isinstance(extract, dict):
        raise RegistryError(f"source {source['id']} must configure JSON extraction")
    required = ("items_path", "id_field", "title_field", "url_field", "revision_field")
    if any(not isinstance(extract.get(field), str) for field in required):
        raise RegistryError(f"source {source['id']} has an invalid JSON extraction contract")
    values = _value_at_path(value, extract["items_path"])
    if not isinstance(values, list):
        raise SourceFetchError(f"source {source['id']} JSON items path is not a list")
    items: list[dict[str, str]] = []
    for value in values:
        if not isinstance(value, dict):
            raise SourceFetchError(f"source {source['id']} contains a non-object JSON item")
        try:
            item = {
                "id": str(value[extract["id_field"]]),
                "title": str(value[extract["title_field"]]),
                "url": str(value[extract["url_field"]]),
                "revision": str(value[extract["revision_field"]]),
            }
        except KeyError as error:
            raise SourceFetchError(
                f"source {source['id']} JSON item is missing field: {error.args[0]}"
            ) from error
        if urlparse(item["url"]).scheme != "https":
            raise SourceFetchError(f"source {source['id']} item URL must use https")
        items.append(item)
    return items


def _atom_items(source: dict[str, Any], body: bytes) -> list[dict[str, str]]:
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise SourceFetchError(f"source {source['id']} Atom feed contains a forbidden declaration")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise SourceFetchError(f"source {source['id']} returned invalid Atom XML") from error
    items: list[dict[str, str]] = []
    for entry in root.findall("{*}entry"):
        identifier = entry.findtext("{*}id")
        title = entry.findtext("{*}title")
        revision = entry.findtext("{*}updated")
        link = entry.find("{*}link")
        url = link.get("href") if link is not None else None
        if not all((identifier, title, revision, url)):
            raise SourceFetchError(f"source {source['id']} Atom entry is missing required fields")
        if urlparse(url).scheme != "https":
            raise SourceFetchError(f"source {source['id']} Atom entry URL must use https")
        items.append({"id": identifier, "title": title, "url": url, "revision": revision})
    return items


def _incremental_items(
    source: dict[str, Any], items: list[dict[str, str]], previous: dict[str, Any], now: str
) -> tuple[list[dict[str, Any]], dict[str, str], str]:
    seen_items = deepcopy(previous.get("seen_items", {}))
    discoveries: list[dict[str, Any]] = []
    revisions: list[str] = []
    for item in items:
        item_hash = sha256_bytes(canonical_json_bytes(item))
        revisions.append(item["revision"])
        if seen_items.get(item["id"]) != item_hash:
            discoveries.append(_item_discovery(source, item, item_hash, now))
            seen_items[item["id"]] = item_hash
    cursor = max(revisions) if revisions else previous.get("cursor", "")
    return discoveries, seen_items, cursor


def _process_source(
    source: dict[str, Any], previous: dict[str, Any], fetcher: Fetcher, now: str
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    response = fetcher.fetch(source["url"], _request_headers(previous))
    if response.status == 304:
        if not previous:
            raise SourceFetchError(f"source {source['id']} returned 304 without prior state")
        updated = deepcopy(previous)
        updated["last_success_at"] = now
        return updated, [], {"source_id": source["id"], "status": "not_modified", "discoveries": 0}
    if response.status != 200:
        raise SourceFetchError(f"source {source['id']} returned HTTP {response.status}")
    if urlparse(response.final_url).scheme != "https":
        raise SourceFetchError(f"source {source['id']} redirected outside https")

    evidence_hash = sha256_bytes(response.body)
    discoveries: list[dict[str, Any]] = []
    seen_items = deepcopy(previous.get("seen_items", {}))
    cursor = evidence_hash
    if previous.get("content_sha256") != evidence_hash:
        if source["adapter"] == "document":
            discoveries.append(_document_discovery(source, response, evidence_hash, now))
        elif source["adapter"] == "json-list":
            discoveries, seen_items, cursor = _incremental_items(
                source, _json_items(source, response.body), previous, now
            )
        elif source["adapter"] == "atom":
            discoveries, seen_items, cursor = _incremental_items(
                source, _atom_items(source, response.body), previous, now
            )

    updated = {
        "adapter": source["adapter"],
        "url": source["url"],
        "etag": response.headers.get("etag"),
        "last_modified": response.headers.get("last-modified"),
        "cursor": cursor,
        "content_sha256": evidence_hash,
        "seen_items": seen_items,
        "last_success_at": now,
    }
    return updated, discoveries, {
        "source_id": source["id"],
        "status": "changed" if discoveries else "unchanged_content",
        "discoveries": len(discoveries),
    }


def _run_id(now: str) -> str:
    return now.replace(":", "-")


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Harvest run {report['run_id']}",
        "",
        f"- Status: `{report['status']}`",
        f"- Sources: {len(report['sources'])}",
        f"- Discoveries: {report['discoveries']}",
        "- Discards: 0",
        "- Merges: 0",
        "- Updates: 0",
        "- Creations: 0",
        "",
        "## Sources",
        "",
    ]
    for source in report["sources"]:
        lines.append(
            f"- `{source['source_id']}`: {source['status']} ({source['discoveries']} discoveries)"
        )
    lines.extend(["", "## Unresolved issues", "", "- None.", ""])
    return "\n".join(lines)


def run_scan(
    root: Path,
    fetcher: Fetcher,
    *,
    now: str,
    source_ids: set[str] | None = None,
) -> dict[str, Any]:
    sources = load_registry(root)
    if source_ids is not None:
        known = {source["id"] for source in sources}
        unknown = source_ids - known
        if unknown:
            raise RegistryError(f"unknown source ids: {', '.join(sorted(unknown))}")
        sources = [source for source in sources if source["id"] in source_ids]

    state_path = root / "state" / "harvest-state.json"
    current_state = load_json(
        state_path, {"schema_version": 1, "last_successful_run": None, "sources": {}}
    )
    staged_state = deepcopy(current_state)
    staged_state["schema_version"] = 1
    staged_discoveries: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []
    run_id = _run_id(now)

    try:
        for source in sources:
            previous = current_state.get("sources", {}).get(source["id"], {})
            source_state, discoveries, result = _process_source(source, previous, fetcher, now)
            staged_state.setdefault("sources", {})[source["id"]] = source_state
            staged_discoveries.extend(discoveries)
            source_results.append(result)
    except (RegistryError, SourceFetchError, OSError) as error:
        failed_report = {
            "schema_version": 1,
            "run_id": run_id,
            "status": "failed",
            "discoveries": 0,
            "sources": source_results,
            "error": f"{type(error).__name__}: {error}",
        }
        atomic_write_json(root / "runs" / f"{run_id}-scan-failed.json", failed_report)
        raise

    staged_state["last_successful_run"] = now
    for discovery in staged_discoveries:
        path = root / "candidates" / "inbox" / f"{discovery['id']}.json"
        if not path.exists():
            atomic_write_json(path, discovery)
    atomic_write_json(state_path, staged_state)

    report = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "changed" if staged_discoveries else "no_op",
        "discoveries": len(staged_discoveries),
        "sources": source_results,
        "decisions": {"discard": 0, "merge": 0, "update": 0, "create": 0},
        "validations": [],
        "unresolved_issues": [],
    }
    atomic_write_json(root / "runs" / f"{run_id}-scan.json", report)
    atomic_write_text(root / "runs" / f"{run_id}-scan.md", _markdown_report(report))
    return report
