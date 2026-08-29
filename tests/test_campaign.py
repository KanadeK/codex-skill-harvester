from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.campaign import run_campaign
from skill_harvester.sources import FetchResponse, SourceFetchError

from _support import write_registry


ROOT = Path(__file__).resolve().parents[1]


class MappingFetcher:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        self.requests.append(url)
        if url.endswith("updates.xml"):
            body = b"<rss><channel><item><guid>package-1</guid><title>package 1</title><pubDate>Wed, 29 Aug 2026 00:00:00 GMT</pubDate><link>https://pypi.org/project/package-1/</link></item></channel></rss>"
        elif url.endswith("releases.atom"):
            body = b"<feed><entry><id>release-1</id><title>v1</title><updated>2026-08-29T00:00:00Z</updated><link href='https://github.com/openai/codex/releases/tag/v1'/></entry></feed>"
        elif "contents/plugins" in url:
            body = b'[{"sha":"abc","name":"plugin","html_url":"https://github.com/openai/plugins/tree/main/plugins/plugin"}]'
        else:
            body = b"# Official workflow\n\nEvidence only."
        return FetchResponse(200, url, {"etag": f'"{len(self.requests)}"'}, body)


class FailingRampFetcher(MappingFetcher):
    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        if "contents/plugins" in url:
            raise SourceFetchError("source returned HTTP 403")
        return super().fetch(url, headers)


class CampaignTests(unittest.TestCase):
    def test_healthy_canary_automatically_ramps_to_registered_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = json.loads((ROOT / "sources" / "registry.json").read_text(encoding="utf-8"))
            policy = json.loads((ROOT / "config" / "campaign-policy.json").read_text(encoding="utf-8"))
            write_registry(root, registry["sources"])
            (root / "config").mkdir()
            (root / "config" / "campaign-policy.json").write_text(
                json.dumps(policy, indent=2) + "\n", encoding="utf-8"
            )
            fetcher = MappingFetcher()

            report = run_campaign(
                root,
                fetcher,
                now="2026-08-29T05:00:00Z",
                ramp=True,
            )

            self.assertEqual(report["status"], "continued")
            self.assertTrue(report["ramped"])
            self.assertEqual(report["registered_endpoints"], 10)
            self.assertEqual(report["canary_endpoints"], 3)
            self.assertEqual(report["metrics"]["source_requests"], 10)
            self.assertGreater(report["metrics"]["downloaded_bytes"], 0)
            self.assertEqual(report["metrics"]["normalized_candidates"], 10)
            self.assertEqual(report["metrics"]["deep_reviews"], 0)
            self.assertEqual(report["metrics"]["usage_credits"], {"measured": False})

    def test_failed_ramp_keeps_a_checkpoint_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = json.loads((ROOT / "sources" / "registry.json").read_text(encoding="utf-8"))
            policy = json.loads((ROOT / "config" / "campaign-policy.json").read_text(encoding="utf-8"))
            policy["source_groups"]["openai-format-authority"]["source_ids"].append(
                "openai-plugin-catalog"
            )
            write_registry(root, registry["sources"])
            (root / "config").mkdir()
            (root / "config" / "campaign-policy.json").write_text(
                json.dumps(policy, indent=2) + "\n", encoding="utf-8"
            )

            report = run_campaign(
                root,
                FailingRampFetcher(),
                now="2026-08-29T06:00:00Z",
                ramp=True,
            )

            self.assertEqual(report["status"], "checkpoint")
            self.assertFalse(report["ramped"])
            self.assertIn("ramp source failure", report["stop_reasons"])
            self.assertIn("HTTP 403", report["ramp_error"])
            self.assertTrue((root / "runs" / "2026-08-29T06-00-00Z-campaign.json").is_file())


if __name__ == "__main__":
    unittest.main()
