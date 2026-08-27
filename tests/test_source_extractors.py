from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.sources import FetchResponse, RegistryError, run_scan

from _support import QueueFetcher, read_json, write_registry


class SourceExtractorTests(unittest.TestCase):
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
            state = read_json(root / "state" / "harvest-state.json")
            self.assertEqual(set(state["sources"]["github-search"]["seen_items"]), {"1", "2", "3"})

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
