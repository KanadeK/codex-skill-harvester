from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.runtime_store import open_runtime_store
from skill_harvester.sources import FetchResponse, run_scan

from _support import QueueFetcher, scan_context, workflow_source, write_registry


class FunnelPipelineTests(unittest.TestCase):
    def test_package_release_feed_is_observation_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = {
                "id": "pypi-updates",
                "adapter": "rss",
                "url": "https://pypi.org/rss/updates.xml",
                "trust": "official",
                "authority": "official-package-feed",
                "license": {"status": "facts-only", "identifier": None},
            }
            write_registry(root, [source])
            body = b"""<rss><channel><item><guid>package-1</guid><title>package 1</title><pubDate>Wed, 29 Aug 2026 00:00:00 GMT</pubDate><link>https://pypi.org/project/package-1/</link></item></channel></rss>"""

            with patch(
                "skill_harvester.runtime_store.RuntimeStore.unpromoted_observations",
                side_effect=AssertionError(
                    "discovery-only sources must not load the normalization backlog"
                ),
            ):
                report = run_scan(
                    root,
                    QueueFetcher(FetchResponse(200, source["url"], {}, body)),
                    now="2026-08-29T08:00:00Z",
                    source_context=scan_context(
                        "pypi-updates",
                        source_group="python-packaging",
                        topic_id="software.publish.python-packaging",
                    ),
                )

            self.assertEqual(report["metrics"]["observations_inserted"], 1)
            self.assertEqual(report["metrics"]["normalized_candidates"], 0)
            with open_runtime_store(root) as store:
                self.assertEqual(store.observation_count(), 1)
                self.assertEqual(store.candidate_count(), 0)
                observation = next(store.observations())
                self.assertEqual(observation["source_group"], "python-packaging")
                self.assertEqual(
                    observation["topic_id"], "software.publish.python-packaging"
                )

    def test_workflow_evidence_reaches_candidate_queue_and_l3_recall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = workflow_source("release-evidence")
            write_registry(root, [source])
            (root / "catalog").mkdir()
            (root / "catalog" / "capabilities.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "internal": [
                            {
                                "id": "internal:release-audit",
                                "fingerprint": source["workflow_signal"]["fingerprint"],
                            }
                        ],
                        "external": [],
                    }
                ),
                encoding="utf-8",
            )
            response = FetchResponse(
                200,
                source["url"],
                {"etag": '"v1"'},
                b"# Verify a release\n\nInspect the release and produce an evidence report.",
            )

            first = run_scan(
                root,
                QueueFetcher(response),
                now="2026-08-29T08:05:00Z",
                source_context=scan_context("release-evidence"),
            )

            self.assertEqual(first["metrics"]["observations_inserted"], 1)
            self.assertEqual(first["metrics"]["normalized_candidates"], 1)
            self.assertEqual(first["metrics"]["l3_recalls"], 1)
            with open_runtime_store(root) as store:
                observation = next(store.observations())
                candidate = next(store.candidates())
                self.assertEqual(candidate["observation_id"], observation["id"])
                self.assertEqual(candidate["topic_id"], "software.validate.delivery")
                self.assertEqual(
                    set(candidate["fingerprint"]),
                    {
                        "goal",
                        "triggers",
                        "inputs",
                        "outputs",
                        "tools",
                        "side_effects",
                        "platforms",
                    },
                )
                self.assertEqual(candidate["l3_recall"][0]["id"], "internal:release-audit")
                self.assertEqual(candidate["queue"], "official-gap")

            second = run_scan(
                root,
                QueueFetcher(FetchResponse(304, source["url"], {"etag": '"v1"'}, b"")),
                now="2026-08-29T08:06:00Z",
                source_context=scan_context("release-evidence"),
            )
            self.assertEqual(second["status"], "no_op")
            self.assertEqual(second["metrics"]["observations_inserted"], 0)
            self.assertEqual(second["metrics"]["normalized_candidates"], 0)

            third = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(
                        200,
                        source["url"],
                        {"etag": '"v2"'},
                        b"# Verify a release\n\nInspect changed release evidence.",
                    )
                ),
                now="2026-08-29T08:07:00Z",
                source_context=scan_context("release-evidence"),
            )
            self.assertEqual(third["metrics"]["normalized_candidates"], 1)
            with open_runtime_store(root) as store:
                candidates = list(store.candidates())
            self.assertEqual(len(candidates), 2)
            self.assertEqual(candidates[1]["l2_matches"], [candidates[0]["id"]])

    def test_all_five_queues_are_assigned_in_the_source_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = [
                workflow_source("urgent", published_impact=True),
                workflow_source("official"),
                workflow_source(
                    "reactivated",
                    trust="representative",
                    operational_authority=False,
                    reactivated=True,
                ),
                workflow_source(
                    "novel", trust="representative", operational_authority=False
                ),
                workflow_source(
                    "representative-authority",
                    trust="representative",
                    operational_authority=True,
                ),
                workflow_source(
                    "aged",
                    trust="representative",
                    operational_authority=False,
                    aged_backlog=True,
                ),
            ]
            write_registry(root, sources)
            (root / "catalog").mkdir()
            (root / "catalog" / "capabilities.json").write_text(
                json.dumps({"schema_version": 2, "internal": [], "external": []}),
                encoding="utf-8",
            )
            fetcher = QueueFetcher(
                *[
                    FetchResponse(200, source["url"], {}, f"# {source['id']}".encode())
                    for source in sources
                ]
            )

            run_scan(
                root,
                fetcher,
                now="2026-08-29T08:10:00Z",
                source_context=scan_context(*(source["id"] for source in sources)),
            )

            with open_runtime_store(root) as store:
                queues = {candidate["source_id"]: candidate["queue"] for candidate in store.candidates()}
            self.assertEqual(
                queues,
                {
                    "urgent": "urgent-impact",
                    "official": "official-gap",
                    "reactivated": "reactivation",
                    "novel": "novel-discovery",
                    "representative-authority": "novel-discovery",
                    "aged": "aged-backlog",
                },
            )


if __name__ == "__main__":
    unittest.main()
