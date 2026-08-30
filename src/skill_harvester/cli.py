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
from .queries import QueryBatchError, export_query_batch, import_query_results
from .production import ProductionReportError, write_production_report
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
from .semantic import SemanticReviewError, export_semantic_batch, import_semantic_review
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
    query_export = commands.add_parser(
        "query-export", help="export or resume a bounded discovery-query batch"
    )
    query_export.add_argument("--root", type=Path, default=Path.cwd())
    query_export.add_argument("--cycle", required=True)
    query_export.add_argument("--limit", type=int, required=True)
    query_export.add_argument("--output", type=Path, required=True)
    query_import = commands.add_parser(
        "query-import", help="import factual results from an executed query batch"
    )
    query_import.add_argument("--root", type=Path, default=Path.cwd())
    query_import.add_argument("--batch", required=True)
    query_import.add_argument("--results", type=Path, required=True)
    semantic_export = commands.add_parser(
        "semantic-export", help="export or resume a bounded observation review batch"
    )
    semantic_export.add_argument("--root", type=Path, default=Path.cwd())
    semantic_export.add_argument("--limit", type=int, required=True)
    semantic_export.add_argument("--output", type=Path, required=True)
    semantic_import = commands.add_parser(
        "semantic-import", help="import Codex-authored Evidence Packs"
    )
    semantic_import.add_argument("--root", type=Path, default=Path.cwd())
    semantic_import.add_argument("--batch", required=True)
    semantic_import.add_argument("--review", type=Path, required=True)
    production_report = commands.add_parser(
        "production-report",
        help="generate an auditable content-production funnel report",
    )
    production_report.add_argument("--root", type=Path, default=Path.cwd())
    production_report.add_argument("--campaign-report", type=Path, required=True)
    production_report.add_argument(
        "--query-report", type=Path, action="append", required=True
    )
    production_report.add_argument(
        "--semantic-report", type=Path, action="append", required=True
    )
    production_report.add_argument(
        "--supplemental-scan", type=Path, action="append", default=[]
    )
    production_report.add_argument("--query-no-op-report", type=Path, required=True)
    production_report.add_argument("--semantic-no-op-report", type=Path, required=True)
    production_report.add_argument("--stable-no-op-scan", type=Path, required=True)
    production_report.add_argument("--output", type=Path, required=True)
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
        observed_at = now or datetime.now(timezone.utc).isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
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
        if args.command == "query-export":
            report = export_query_batch(
                root,
                now=observed_at,
                cycle_id=args.cycle,
                limit=args.limit,
                output_path=args.output.resolve(),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "query-import":
            report = import_query_results(
                root,
                batch_id=args.batch,
                results_path=args.results.resolve(),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "semantic-export":
            report = export_semantic_batch(
                root,
                now=observed_at,
                limit=args.limit,
                output_path=args.output.resolve(),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "semantic-import":
            report = import_semantic_review(
                root,
                batch_id=args.batch,
                review_path=args.review.resolve(),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
        if args.command == "production-report":
            report = write_production_report(
                root,
                generated_at=observed_at,
                campaign_report_path=args.campaign_report.resolve(),
                query_report_paths=[path.resolve() for path in args.query_report],
                semantic_report_paths=[path.resolve() for path in args.semantic_report],
                supplemental_scan_paths=[
                    path.resolve() for path in args.supplemental_scan
                ],
                query_no_op_report_path=args.query_no_op_report.resolve(),
                semantic_no_op_report_path=args.semantic_no_op_report.resolve(),
                stable_no_op_scan_path=args.stable_no_op_scan.resolve(),
                output_path=args.output.resolve(),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0
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
        QueryBatchError,
        ProductionReportError,
        RuntimeStoreError,
        SemanticReviewError,
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
