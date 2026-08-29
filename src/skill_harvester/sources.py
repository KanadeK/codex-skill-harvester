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
    atomic_write_text,
    canonical_json_bytes,
    load_json,
    sha256_bytes,
)
from .fingerprints import FingerprintError, normalize_fingerprint, recall_capabilities
from .runtime_store import open_runtime_store


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
        if source.get("adapter") not in {"document", "json-list", "atom", "rss"}:
            raise RegistryError(f"source {source_id} has an unsupported adapter")
        change_policy = source.get("change_policy", "revision")
        if change_policy not in {"revision", "material"}:
            raise RegistryError(f"source {source_id} has an unsupported change policy")
        if "change_policy" in source and source["adapter"] != "json-list":
            raise RegistryError(f"source {source_id} change policy requires the json-list adapter")
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
        workflow_signal = source.get("workflow_signal")
        if workflow_signal is not None:
            if not isinstance(workflow_signal, dict):
                raise RegistryError(f"source {source_id} workflow signal must be an object")
            if not isinstance(workflow_signal.get("operational_authority"), bool):
                raise RegistryError(
                    f"source {source_id} workflow signal must declare operational_authority"
                )
            try:
                normalize_fingerprint(workflow_signal.get("fingerprint"))
            except FingerprintError as error:
                raise RegistryError(
                    f"source {source_id} workflow signal is invalid: {error}"
                ) from error
            for flag in ("published_impact", "reactivated", "aged_backlog"):
                if flag in workflow_signal and not isinstance(workflow_signal[flag], bool):
                    raise RegistryError(
                        f"source {source_id} workflow signal {flag} must be boolean"
                    )
    return sources


def _request_headers(previous: dict[str, Any]) -> dict[str, str]:
    headers = {"Accept": "application/json, application/atom+xml, text/plain, text/html"}
    if previous.get("etag"):
        headers["If-None-Match"] = previous["etag"]
    if previous.get("last_modified"):
        headers["If-Modified-Since"] = previous["last_modified"]
    return headers


def _document_observation(
    source: dict[str, Any], response: FetchResponse, evidence_hash: str, now: str
) -> dict[str, Any]:
    text = response.body.decode("utf-8", errors="replace")
    headings = [match.group(1).strip() for match in re.finditer(r"(?m)^#{1,3}\s+(.+?)\s*$", text)]
    title = headings[0] if headings else source["id"]
    observation_id = sha256_bytes(f"{source['id']}:{evidence_hash}".encode())[:24]
    revision = response.headers.get("etag") or response.headers.get("last-modified") or evidence_hash
    return {
        "schema_version": 2,
        "id": observation_id,
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
    }


def _item_observation(
    source: dict[str, Any], item: dict[str, Any], item_hash: str, now: str
) -> dict[str, Any]:
    observation_id = sha256_bytes(f"{source['id']}:{item['id']}:{item_hash}".encode())[:24]
    return {
        "schema_version": 2,
        "id": observation_id,
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


def _rss_items(source: dict[str, Any], body: bytes) -> list[dict[str, str]]:
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise SourceFetchError(f"source {source['id']} RSS feed contains a forbidden declaration")
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as error:
        raise SourceFetchError(f"source {source['id']} returned invalid RSS XML") from error
    items: list[dict[str, str]] = []
    for entry in root.findall(".//item"):
        identifier = entry.findtext("guid") or entry.findtext("link")
        title = entry.findtext("title")
        revision = entry.findtext("pubDate") or entry.findtext("date")
        url = entry.findtext("link")
        if not all((identifier, title, revision, url)):
            raise SourceFetchError(f"source {source['id']} RSS item is missing required fields")
        if urlparse(url).scheme != "https":
            raise SourceFetchError(f"source {source['id']} RSS item URL must use https")
        items.append({"id": identifier, "title": title, "url": url, "revision": revision})
    return items


def _incremental_items(
    source: dict[str, Any], items: list[dict[str, str]], previous: dict[str, Any], now: str
) -> tuple[
    list[dict[str, Any]],
    dict[str, str],
    dict[str, str],
    list[str],
    bool,
    str,
]:
    seen_items = deepcopy(previous.get("seen_items", {}))
    material_items = deepcopy(previous.get("material_items", {}))
    discoveries: list[dict[str, Any]] = []
    revisions: list[str] = []
    window_item_ids = [item["id"] for item in items]
    previous_window = previous.get("window_item_ids")
    window_changed = isinstance(previous_window, list) and previous_window != window_item_ids
    for item in items:
        item_hash = sha256_bytes(canonical_json_bytes(item))
        material_hash = sha256_bytes(
            canonical_json_bytes({field: item[field] for field in ("id", "title", "url")})
        )
        revisions.append(item["revision"])
        if source.get("change_policy", "revision") == "material":
            previous_material = material_items.get(item["id"])
            changed = item["id"] not in seen_items or (
                previous_material is not None and previous_material != material_hash
            )
        else:
            changed = seen_items.get(item["id"]) != item_hash
        if changed:
            discoveries.append(_item_observation(source, item, item_hash, now))
        seen_items[item["id"]] = item_hash
        material_items[item["id"]] = material_hash
    cursor = max(revisions) if revisions else previous.get("cursor", "")
    return discoveries, seen_items, material_items, window_item_ids, window_changed, cursor


def _process_source(
    source: dict[str, Any], previous: dict[str, Any], fetcher: Fetcher, now: str
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    conditional_state = previous if previous.get("url") == source["url"] else {}
    response = fetcher.fetch(source["url"], _request_headers(conditional_state))
    if response.status == 304:
        if not previous:
            raise SourceFetchError(f"source {source['id']} returned 304 without prior state")
        updated = deepcopy(previous)
        updated["last_success_at"] = now
        return updated, [], {
            "source_id": source["id"],
            "status": "not_modified",
            "observations_staged": 0,
            "raw_observations": 0,
            "downloaded_bytes": 0,
        }
    if response.status != 200:
        raise SourceFetchError(f"source {source['id']} returned HTTP {response.status}")
    if urlparse(response.final_url).scheme != "https":
        raise SourceFetchError(f"source {source['id']} redirected outside https")

    evidence_hash = sha256_bytes(response.body)
    discoveries: list[dict[str, Any]] = []
    seen_items = deepcopy(previous.get("seen_items", {}))
    material_items = deepcopy(previous.get("material_items", {}))
    window_item_ids = deepcopy(previous.get("window_item_ids", []))
    window_changed = False
    cursor = evidence_hash
    observations = 0
    if previous.get("content_sha256") != evidence_hash:
        if source["adapter"] == "document":
            discoveries.append(_document_observation(source, response, evidence_hash, now))
            observations = 1
        elif source["adapter"] == "json-list":
            items = _json_items(source, response.body)
            observations = len(items)
            (
                discoveries,
                seen_items,
                material_items,
                window_item_ids,
                window_changed,
                cursor,
            ) = _incremental_items(
                source, items, previous, now
            )
        elif source["adapter"] == "atom":
            items = _atom_items(source, response.body)
            observations = len(items)
            (
                discoveries,
                seen_items,
                material_items,
                window_item_ids,
                window_changed,
                cursor,
            ) = _incremental_items(
                source, items, previous, now
            )
        elif source["adapter"] == "rss":
            items = _rss_items(source, response.body)
            observations = len(items)
            (
                discoveries,
                seen_items,
                material_items,
                window_item_ids,
                window_changed,
                cursor,
            ) = _incremental_items(
                source, items, previous, now
            )

    updated = {
        "adapter": source["adapter"],
        "url": source["url"],
        "etag": response.headers.get("etag"),
        "last_modified": response.headers.get("last-modified"),
        "cursor": cursor,
        "content_sha256": evidence_hash,
        "seen_items": seen_items,
        "material_items": material_items,
        "window_item_ids": window_item_ids,
        "last_success_at": now,
    }
    result_status = "changed" if discoveries else "window_changed" if window_changed else "unchanged_content"
    return updated, discoveries, {
        "source_id": source["id"],
        "status": result_status,
        "observations_staged": len(discoveries),
        "window_changed": window_changed,
        "raw_observations": observations,
        "downloaded_bytes": len(response.body),
    }


def _run_id(now: str) -> str:
    return now.replace(":", "-")


def _scan_metrics(
    *,
    selected: int,
    succeeded: int,
    failed: int,
    staged: int,
    inserted: int,
    observation_duplicates: int,
    normalized_candidates: int,
    candidate_duplicates: int,
    l3_recalls: int,
    raw_observations: int,
    downloaded_bytes: int,
) -> dict[str, Any]:
    return {
        "source_requests": selected,
        "sources_succeeded": succeeded,
        "failures": failed,
        "source_success_rate": succeeded / selected,
        "raw_observations": raw_observations,
        "observations_staged": staged,
        "observations_inserted": inserted,
        "observation_duplicates": observation_duplicates,
        "normalized_candidates": normalized_candidates,
        "candidate_duplicates": candidate_duplicates,
        "l3_recalls": l3_recalls,
        "downloaded_bytes": downloaded_bytes,
        "deep_reviews": {"measured": False},
    }


def _candidate_from_observation(
    source: dict[str, Any],
    observation: dict[str, Any],
    catalog: dict[str, Any],
    store: Any,
) -> dict[str, Any] | None:
    signal = source.get("workflow_signal")
    if signal is None:
        return None
    fingerprint = normalize_fingerprint(signal["fingerprint"])
    candidate_id = sha256_bytes(
        b"candidate\0"
        + observation["id"].encode("utf-8")
        + b"\0"
        + canonical_json_bytes(fingerprint)
    )[:24]
    candidate = {
        "schema_version": 2,
        "id": candidate_id,
        "observation_id": observation["id"],
        "source_id": observation["source_id"],
        "source_group": observation["source_group"],
        "topic_id": observation["topic_id"],
        "observed_at": observation["observed_at"],
        "title": observation["title"],
        "canonical_url": observation["canonical_url"],
        "evidence_sha256": observation["evidence_sha256"],
        "trust": observation["trust"],
        "license": observation["license"],
        "fingerprint": fingerprint,
        "l2_matches": store.l2_matches(fingerprint),
        "l3_recall": recall_capabilities(fingerprint, catalog, limit=30),
        "review_status": "pending",
        "operational_authority": signal["operational_authority"],
    }
    for flag in ("published_impact", "reactivated", "aged_backlog"):
        if signal.get(flag):
            candidate[flag] = True
    return candidate


def _markdown_report(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        f"# Harvest run {report['run_id']}",
        "",
        f"- Status: `{report['status']}`",
        f"- Sources: {len(report['sources'])}",
        f"- Observations inserted: {metrics['observations_inserted']}",
        f"- Candidates normalized: {metrics['normalized_candidates']}",
        f"- L3 recalls: {metrics['l3_recalls']}",
        "- Semantic decisions: not run in the discovery stage",
        "",
        "## Sources",
        "",
    ]
    for source in report["sources"]:
        lines.append(
            f"- `{source['source_id']}`: {source['status']} "
            f"({source['observations_staged']} staged observations)"
        )
    lines.extend(["", "## Unresolved issues", "", "- None.", ""])
    return "\n".join(lines)


def run_scan(
    root: Path,
    fetcher: Fetcher,
    *,
    now: str,
    source_ids: set[str] | None = None,
    source_context: dict[str, dict[str, str]],
) -> dict[str, Any]:
    sources = load_registry(root)
    if source_ids is not None:
        known = {source["id"] for source in sources}
        unknown = source_ids - known
        if unknown:
            raise RegistryError(f"unknown source ids: {', '.join(sorted(unknown))}")
        sources = [source for source in sources if source["id"] in source_ids]

    selected_ids = {source["id"] for source in sources}
    if set(source_context) != selected_ids:
        raise RegistryError("source context must exactly cover the selected sources")
    for source_id, context in source_context.items():
        if (
            not isinstance(context, dict)
            or not isinstance(context.get("source_group"), str)
            or not context["source_group"]
            or not isinstance(context.get("topic_id"), str)
            or not context["topic_id"]
        ):
            raise RegistryError(f"source context is invalid: {source_id}")

    store = open_runtime_store(root)
    staged_state: dict[str, dict[str, Any]] = {}
    staged_observations: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []
    run_id = _run_id(now)

    try:
        for source in sources:
            previous = store.source_state(source["id"])
            source_state, observations, result = _process_source(source, previous, fetcher, now)
            staged_state[source["id"]] = source_state
            context = source_context[source["id"]]
            for observation in observations:
                observation["source_group"] = context["source_group"]
                observation["topic_id"] = context["topic_id"]
            staged_observations.extend(observations)
            result.update(context)
            source_results.append(result)
    except (RegistryError, SourceFetchError, OSError) as error:
        failed_report = {
            "schema_version": 2,
            "report_type": "scan",
            "run_id": run_id,
            "status": "failed",
            "observations": 0,
            "sources": source_results,
            "failed_source_id": source["id"],
            "metrics": _scan_metrics(
                selected=len(sources),
                succeeded=len(source_results),
                failed=1,
                staged=len(staged_observations),
                inserted=0,
                observation_duplicates=0,
                normalized_candidates=0,
                candidate_duplicates=0,
                l3_recalls=0,
                raw_observations=sum(
                    item.get("raw_observations", 0) for item in source_results
                ),
                downloaded_bytes=sum(item.get("downloaded_bytes", 0) for item in source_results),
            ),
            "error": f"{type(error).__name__}: {error}",
        }
        store.record_failed_run(failed_report)
        atomic_write_text(
            root / "runs" / f"{run_id}-scan-failed.json",
            json.dumps(failed_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        store.close()
        raise
    except BaseException:
        store.close()
        raise

    source_by_id = {source["id"]: source for source in sources}
    signaled_sources = {
        source_id for source_id, source in source_by_id.items() if "workflow_signal" in source
    }
    observations_to_normalize = (
        {
            observation["id"]: observation
            for observation in store.unpromoted_observations(signaled_sources)
        }
        if signaled_sources
        else {}
    )
    observations_to_normalize.update(
        {
            observation["id"]: observation
            for observation in staged_observations
            if observation["source_id"] in signaled_sources
        }
    )
    catalog: dict[str, Any] = (
        load_json(root / "catalog" / "capabilities.json")
        if signaled_sources
        else {"schema_version": 2, "internal": [], "external": []}
    )
    staged_candidates = [
        candidate
        for observation in observations_to_normalize.values()
        if observation["source_id"] in signaled_sources
        for candidate in [
            _candidate_from_observation(
                source_by_id[observation["source_id"]], observation, catalog, store
            )
        ]
        if candidate is not None
    ]
    committed = store.commit_scan(
        now=now,
        source_states=staged_state,
        observations=staged_observations,
        candidates=staged_candidates,
    )

    report = {
        "schema_version": 2,
        "report_type": "scan",
        "run_id": run_id,
        "status": (
            "changed"
            if committed["observations_inserted"]
            or committed["normalized_candidates"]
            else "no_op"
        ),
        "observations": committed["observations_inserted"],
        "sources": source_results,
        "metrics": _scan_metrics(
            selected=len(sources),
            succeeded=len(source_results),
            failed=0,
            staged=len(staged_observations),
            inserted=committed["observations_inserted"],
            observation_duplicates=committed["observation_duplicates"],
            normalized_candidates=committed["normalized_candidates"],
            candidate_duplicates=committed["candidate_duplicates"],
            l3_recalls=committed["l3_recalls"],
            raw_observations=sum(
                item.get("raw_observations", 0) for item in source_results
            ),
            downloaded_bytes=sum(item.get("downloaded_bytes", 0) for item in source_results),
        ),
        "validations": [],
        "unresolved_issues": [],
    }
    store.record_run(report)
    store.close()
    atomic_write_text(
        root / "runs" / f"{run_id}-scan.json",
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(root / "runs" / f"{run_id}-scan.md", _markdown_report(report))
    return report
