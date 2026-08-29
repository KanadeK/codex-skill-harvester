from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def audit(snapshot: dict[str, Any]) -> dict[str, Any]:
    repository = snapshot["repository"]
    release = snapshot["release"]
    tag = snapshot["tag"]
    checks: list[dict[str, str]] = []

    def add(gate: str, status: str, evidence: str) -> None:
        checks.append({"gate": gate, "status": status, "evidence": evidence})

    add("repository_public", "PASS" if repository["is_private"] is False else "FAIL", repository["url"])
    published = release["is_draft"] is False and bool(release["published_at"])
    add("release_published", "PASS" if published else "FAIL", release["url"])
    immutable_required = snapshot.get("requirements", {}).get("immutable_release", False)
    immutable = release.get("immutable")
    add(
        "release_immutable",
        "PASS" if not immutable_required or immutable is True else "FAIL",
        f"required={str(immutable_required).lower()} immutable={str(immutable).lower()}",
    )
    aligned = release["tag_name"] == tag["name"] and release["target_commit_sha"] == tag["commit_sha"]
    add("tag_target_alignment", "PASS" if aligned else "FAIL", f"tag={tag['commit_sha']} target={release['target_commit_sha']}")

    expected = set(snapshot["expected_assets"])
    actual = set(release["asset_names"])
    missing = sorted(expected - actual)
    add("expected_assets", "PASS" if not missing else "FAIL", "missing=" + (",".join(missing) or "none"))

    attestations_required = snapshot.get("requirements", {}).get(
        "asset_attestations", False
    )
    attestations = {
        item["asset_name"]: item
        for item in snapshot.get("attestations", [])
        if item.get("verified") is True
    }
    unverified_assets = sorted(expected - set(attestations))
    add(
        "asset_attestations",
        "PASS" if not attestations_required or not unverified_assets else "FAIL",
        "not required"
        if not attestations_required
        else "unverified=" + (",".join(unverified_assets) or "none"),
    )

    pull_request = snapshot["pull_request"]
    if pull_request is None:
        add("pull_request_merged", "NOT_CHECKED", "no pull request supplied")
        add("pull_request_checks", "NOT_CHECKED", "no pull request supplied")
        add("pull_request_release_alignment", "NOT_CHECKED", "no pull request supplied")
    else:
        add("pull_request_merged", "PASS" if pull_request["state"] == "MERGED" else "FAIL", pull_request["url"])
        buckets = [item["bucket"] for item in pull_request["checks"]]
        checks_pass = bool(buckets) and all(bucket in {"pass", "skipping"} for bucket in buckets)
        add("pull_request_checks", "PASS" if checks_pass else "FAIL", "buckets=" + (",".join(buckets) or "none"))
        merge_aligned = pull_request["merge_commit_sha"] == tag["commit_sha"]
        add("pull_request_release_alignment", "PASS" if merge_aligned else "FAIL", f"merge={pull_request['merge_commit_sha']} tag={tag['commit_sha']}")

    installation = snapshot["installation"]
    if installation is None:
        add("installation_or_invocation", "NOT_CHECKED", "no isolated acceptance run recorded")
    else:
        add("installation_or_invocation", "PASS" if installation["exit_code"] == 0 else "FAIL", installation["command"])

    failed = any(item["status"] == "FAIL" for item in checks)
    unchecked = any(item["status"] == "NOT_CHECKED" for item in checks)
    result = "incomplete" if failed else "unverified" if unchecked else "complete"
    return {"result": result, "checks": checks, "contributors": [item["login"] for item in snapshot["contributors"]]}


def _cell(value: str) -> str:
    return " ".join(value.splitlines()).replace("|", "\\|")


def render(report: dict[str, Any]) -> str:
    lines = [f"# Release audit: {report['result']}", "", "| Gate | Status | Evidence |", "| --- | --- | --- |"]
    for item in report["checks"]:
        lines.append(f"| {item['gate']} | {item['status']} | {_cell(item['evidence'])} |")
    contributors = ", ".join(_cell(login) for login in report["contributors"])
    lines.extend(["", "Contributors: " + (contributors or "none reported"), ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a normalized GitHub release evidence snapshot.")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    report = audit(snapshot)
    markdown = render(report)
    if args.output:
        args.output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 1 if report["result"] == "incomplete" else 0


if __name__ == "__main__":
    raise SystemExit(main())
