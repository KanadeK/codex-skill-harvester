from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .sources import Fetcher, RegistryError, SourceFetchError, UrllibFetcher, run_scan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-harvester",
        description="Incrementally scan registered public workflow evidence.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("scan", help="scan changed sources and persist successful cursors")
    scan.add_argument("--root", type=Path, default=Path.cwd(), help="harvester repository root")
    scan.add_argument("--source", action="append", help="scan only this registered source id")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    fetcher: Fetcher | None = None,
    now: str | None = None,
) -> int:
    args = _parser().parse_args(argv)
    observed_at = now or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    try:
        report = run_scan(
            args.root.resolve(),
            fetcher or UrllibFetcher(),
            now=observed_at,
            source_ids=set(args.source) if args.source else None,
        )
    except (RegistryError, SourceFetchError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"status={report['status']} discoveries={report['discoveries']} run={report['run_id']}")
    return 0
