from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.sources import FetchResponse, RegistryError, run_scan

from _support import QueueFetcher, runtime_source_state, write_registry


class SourceExtractorTests(unittest.TestCase):
    def test_material_policy_separates_window_churn_from_real_item_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = {
                "id": "github-search",
                "adapter": "json-list",
                "url": "https://api.github.com/search/repositories?q=agent-skills",
                "trust": "discovery",
                "authority": "demand-signal",
                "license": {"status": "unknown", "identifier": None},
                "change_policy": "material",
                "extract": {
                    "items_path": "items",
                    "id_field": "id",
                    "title_field": "full_name",
                    "url_field": "html_url",
                    "revision_field": "updated_at",
                },
            }
            write_registry(root, [source])

            first_body = json.dumps(
                {
                    "items": [
                        {
                            "id": 1,
                            "full_name": "example/one",
                            "html_url": "https://github.com/example/one",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "full_name": "example/two",
                            "html_url": "https://github.com/example/two",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                    ]
                }
            ).encode()
            first = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, "https://api.github.com/search/repositories", {}, first_body)
                ),
                now="2026-08-27T03:00:00Z",
            )
            self.assertEqual(first["discoveries"], 2)

            reordered_revision_only = json.dumps(
                {
                    "items": [
                        {
                            "id": 2,
                            "full_name": "example/two",
                            "html_url": "https://github.com/example/two",
                            "updated_at": "2026-08-27T00:00:00Z",
                        },
                        {
                            "id": 1,
                            "full_name": "example/one",
                            "html_url": "https://github.com/example/one",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                    ]
                }
            ).encode()
            second = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(
                        200,
                        "https://api.github.com/search/repositories",
                        {},
                        reordered_revision_only,
                    )
                ),
                now="2026-08-27T03:05:00Z",
            )

            self.assertEqual(second["status"], "no_op")
            self.assertEqual(second["discoveries"], 0)
            self.assertEqual(second["sources"][0]["status"], "window_changed")
            self.assertTrue(second["sources"][0]["window_changed"])

            changed_body = json.dumps(
                {
                    "items": [
                        {
                            "id": 2,
                            "full_name": "example/two-renamed",
                            "html_url": "https://github.com/example/two",
                            "updated_at": "2026-08-27T00:00:00Z",
                        },
                        {
                            "id": 3,
                            "full_name": "example/three",
                            "html_url": "https://github.com/example/three",
                            "updated_at": "2026-08-27T00:00:00Z",
                        },
                    ]
                }
            ).encode()
            third = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, "https://api.github.com/search/repositories", {}, changed_body)
                ),
                now="2026-08-27T03:10:00Z",
            )

            self.assertEqual(third["status"], "changed")
            self.assertEqual(third["discoveries"], 2)
            search_state = runtime_source_state(root, "github-search")
            self.assertEqual(set(search_state["material_items"]), {"1", "2", "3"})
            self.assertEqual(search_state["window_item_ids"], ["2", "3"])

    def test_json_list_emits_only_new_or_changed_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(
                root,
                [
                    {
                        "id": "github-search",
                        "adapter": "json-list",
                        "url": "https://api.github.com/search/repositories?q=agent-skills",
                        "trust": "discovery",
                        "authority": "demand-signal",
                        "license": {"status": "unknown", "identifier": None},
                        "extract": {
                            "items_path": "items",
                            "id_field": "id",
                            "title_field": "full_name",
                            "url_field": "html_url",
                            "revision_field": "updated_at",
                        },
                    }
                ],
            )
            first_body = json.dumps(
                {
                    "items": [
                        {
                            "id": 1,
                            "full_name": "example/one",
                            "html_url": "https://github.com/example/one",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "full_name": "example/two",
                            "html_url": "https://github.com/example/two",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                    ]
                }
            ).encode()
            first = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, "https://api.github.com/search/repositories", {}, first_body)
                ),
                now="2026-08-27T03:00:00Z",
            )
            self.assertEqual(first["discoveries"], 2)

            second_body = json.dumps(
                {
                    "items": [
                        {
                            "id": 1,
                            "full_name": "example/one",
                            "html_url": "https://github.com/example/one",
                            "updated_at": "2026-08-26T00:00:00Z",
                        },
                        {
                            "id": 2,
                            "full_name": "example/two",
                            "html_url": "https://github.com/example/two",
                            "updated_at": "2026-08-27T00:00:00Z",
                        },
                        {
                            "id": 3,
                            "full_name": "example/three",
                            "html_url": "https://github.com/example/three",
                            "updated_at": "2026-08-27T00:00:00Z",
                        },
                    ]
                }
            ).encode()
            second = run_scan(
                root,
                QueueFetcher(
                    FetchResponse(200, "https://api.github.com/search/repositories", {}, second_body)
                ),
                now="2026-08-27T03:05:00Z",
            )

            self.assertEqual(second["discoveries"], 2)
            self.assertEqual(
                set(runtime_source_state(root, "github-search")["seen_items"]),
                {"1", "2", "3"},
            )

    def test_atom_feed_uses_entry_ids_for_incremental_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(
                root,
                [
                    {
                        "id": "codex-releases",
                        "adapter": "atom",
                        "url": "https://github.com/openai/codex/releases.atom",
                        "trust": "official",
                        "authority": "release-changelog",
                        "license": {"status": "facts-only", "identifier": None},
                    }
                ],
            )
            body = b"""<?xml version='1.0' encoding='utf-8'?>
<feed xmlns='http://www.w3.org/2005/Atom'>
  <entry><id>tag:github.com,2008:Release/1</id><title>v1</title><updated>2026-08-27T00:00:00Z</updated><link href='https://github.com/openai/codex/releases/tag/v1'/></entry>
</feed>"""
            first = run_scan(
                root,
                QueueFetcher(FetchResponse(200, "https://github.com/openai/codex/releases.atom", {}, body)),
                now="2026-08-27T04:00:00Z",
            )
            second = run_scan(
                root,
                QueueFetcher(FetchResponse(200, "https://github.com/openai/codex/releases.atom", {}, body)),
                now="2026-08-27T04:05:00Z",
            )

            self.assertEqual(first["discoveries"], 1)
            self.assertEqual(second["status"], "no_op")

    def test_rss_feed_uses_guid_for_incremental_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(
                root,
                [
                    {
                        "id": "pypi-updates",
                        "adapter": "rss",
                        "url": "https://pypi.org/rss/updates.xml",
                        "trust": "official",
                        "authority": "official-package-feed",
                        "license": {"status": "facts-only", "identifier": None},
                    }
                ],
            )
            body = b"""<?xml version='1.0' encoding='utf-8'?>
<rss version='2.0'><channel><item><guid>package-1</guid><title>package 1</title><pubDate>Wed, 29 Aug 2026 00:00:00 GMT</pubDate><link>https://pypi.org/project/package-1/</link></item></channel></rss>"""

            first = run_scan(
                root,
                QueueFetcher(FetchResponse(200, "https://pypi.org/rss/updates.xml", {}, body)),
                now="2026-08-29T04:00:00Z",
            )
            second = run_scan(
                root,
                QueueFetcher(FetchResponse(200, "https://pypi.org/rss/updates.xml", {}, body)),
                now="2026-08-29T04:05:00Z",
            )

            self.assertEqual(first["discoveries"], 1)
            self.assertEqual(second["status"], "no_op")

    def test_registry_rejects_non_https_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(
                root,
                [
                    {
                        "id": "unsafe",
                        "adapter": "document",
                        "url": "http://example.test/source",
                        "trust": "discovery",
                        "authority": "signal",
                        "license": {"status": "unknown", "identifier": None},
                    }
                ],
            )

            with self.assertRaisesRegex(RegistryError, "https"):
                run_scan(root, QueueFetcher(), now="2026-08-27T05:00:00Z")

    def test_registry_rejects_arbitrary_authentication_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_registry(
                root,
                [
                    {
                        "id": "unsafe-auth",
                        "adapter": "document",
                        "url": "https://api.github.com/resource",
                        "trust": "discovery",
                        "authority": "signal",
                        "license": {"status": "unknown", "identifier": None},
                        "authentication": {"type": "optional-bearer-env", "env": "ARBITRARY_SECRET"},
                    }
                ],
            )

            with self.assertRaisesRegex(RegistryError, "authentication"):
                run_scan(root, QueueFetcher(), now="2026-08-27T05:00:00Z")


if __name__ == "__main__":
    unittest.main()
