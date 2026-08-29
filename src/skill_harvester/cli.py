from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .decisions import DecisionError, apply_decision
from .campaign import (
    CampaignPolicyError,
    campaign_source_context,
    load_campaign_policy,
    run_campaign,
)
from .io import atomic_write_json
from .reporting import (
    ReportingError,
    render_review_queue,
    render_status,
    repository_status,
    review_queue,
)
from .scaling import ScalePolicyError
from .runtime_store import RuntimeStoreError
from .runtime_store import import_legacy_runtime
from .sources import (
    Fetcher,
    GitHubCliFetcher,
    RegistryError,
    SourceFetchError,
    UrllibFetcher,
    run_scan,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-harvester",
        description="Incrementally scan registered public workflow evidence.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="scan changed sources and persist successful cursors")
    scan.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    scan.add_argument("--source", action="append", help="scan only this registered source id")
    scan.add_argument(
        "--source-group",
        help="source group for an explicitly selected source outside campaign policy",
    )
    scan.add_argument(
        "--topic",
        help="topic id for an explicitly selected source outside campaign policy",
    )
    scan.add_argument(
        "--github-auth",
        choices=("environment", "gh-cli"),
        default="environment",
        help="authenticate api.github.com with GITHUB_TOKEN or the official gh keyring",
    )
    apply = commands.add_parser("apply", help="apply one explicit Codex-reviewed decision")
    apply.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    apply.add_argument("--decision", type=Path, required=True, help="reviewed decision JSON path")
    status = commands.add_parser("status", help="show durable source, queue, decision, and catalog state")
    status.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    status.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    queue = commands.add_parser("review-queue", help="list normalized candidates pending Codex review")
    queue.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    queue.add_argument("--source", help="filter by one registered source id")
    queue.add_argument(
        "--limit",
        type=int,
        help=(
            "return at most this many candidates; default and maximum come from "
            "config/scale-policy.json"
        ),
    )
    queue.add_argument("--after", help="resume after this candidate id")
    queue.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    migrate = commands.add_parser(
        "migrate-runtime",
        help="one-time import of legacy Git-JSON runtime records into SQLite",
    )
    migrate.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    migrate.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    campaign = commands.add_parser(
        "campaign",
        help="run the configured three-group canary and optionally ramp within stop-loss",
    )
    campaign.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    campaign.add_argument("--ramp", action="store_true", help="continue to remaining registered campaign sources when the canary is healthy")
    campaign.add_argument(
        "--github-auth",
        choices=("environment", "gh-cli"),
        default="environment",
        help="authenticate api.github.com with GITHUB_TOKEN or the official gh keyring",
    )
    campaign.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    fetcher: Fetcher | None = None,
    now: str | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "migrate-runtime":
            report = import_legacy_runtime(root)
            atomic_write_json(root / "runs" / "runtime-migration.json", report)
            print(json.dumps(report, indent=2, sort_keys=True) if args.json else "runtime migration complete")
            return 0
        if args.command == "status":
            report = repository_status(root)
            print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_status(report))
            return 0
        if args.command == "review-queue":
            report = review_queue(
                root,
                args.source,
                limit=args.limit,
                after=args.after,
            )
            print(
                json.dumps(report, indent=2, sort_keys=True)
                if args.json
                else render_review_queue(report)
            )
            return 0
        if args.command == "apply":
            record = apply_decision(root, args.decision.resolve())
            print(f"outcome={record['outcome']} candidate={record['candidate_id']}")
            return 0
        observed_at = now or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        selected_fetcher = fetcher or (
            GitHubCliFetcher() if args.github_auth == "gh-cli" else UrllibFetcher()
        )
        if args.command == "campaign":
            report = run_campaign(
                root,
                selected_fetcher,
                now=observed_at,
                ramp=args.ramp,
            )
            print(
                json.dumps(report, indent=2, sort_keys=True)
                if args.json
                else (
                    f"status={report['status']} "
                    f"observations={report['metrics']['observations_inserted']} "
                    f"candidates={report['metrics']['normalized_candidates']} "
                    f"run={report['run_id']}"
                )
            )
            return 0
        if args.source_group is not None or args.topic is not None:
            if not args.source or not args.source_group or not args.topic:
                raise RegistryError(
                    "manual source context requires --source, --source-group, and --topic"
                )
            selected_sources = set(args.source)
            selected_contexts = {
                source_id: {
                    "source_group": args.source_group,
                    "topic_id": args.topic,
                }
                for source_id in selected_sources
            }
        else:
            policy = load_campaign_policy(root)
            contexts = campaign_source_context(policy)
            selected_sources = set(args.source) if args.source else set(contexts)
            outside_campaign = selected_sources - set(contexts)
            if outside_campaign:
                raise RegistryError(
                    "sources outside campaign policy require --source-group and --topic"
                )
            selected_contexts = {
                source_id: contexts[source_id] for source_id in selected_sources
            }
        report = run_scan(
            root,
            selected_fetcher,
            now=observed_at,
            source_ids=selected_sources,
            source_context=selected_contexts,
        )
    except (
        DecisionError,
        RegistryError,
        ReportingError,
        ScalePolicyError,
        CampaignPolicyError,
        RuntimeStoreError,
        SourceFetchError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        f"status={report['status']} "
        f"observations={report['metrics']['observations_inserted']} "
        f"candidates={report['metrics']['normalized_candidates']} "
        f"run={report['run_id']}"
    )
    return 0
