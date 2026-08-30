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


class FailingCanaryFetcher(MappingFetcher):
    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        if url.endswith("skills.md"):
            self.requests.append(url)
            raise SourceFetchError("canary unavailable")
        return super().fetch(url, headers)


class ChangingPyPIFetcher(MappingFetcher):
    def __init__(self, package_id: str) -> None:
        super().__init__()
        self.package_id = package_id

    def fetch(self, url: str, headers: dict[str, str]) -> FetchResponse:
        if url.endswith("updates.xml"):
            self.requests.append(url)
            body = (
                "<rss><channel><item>"
                f"<guid>{self.package_id}</guid><title>{self.package_id}</title>"
                "<pubDate>Wed, 29 Aug 2026 00:00:00 GMT</pubDate>"
                f"<link>https://pypi.org/project/{self.package_id}/</link>"
                "</item></channel></rss>"
            ).encode()
            return FetchResponse(200, url, {}, body)
        return super().fetch(url, headers)


def write_campaign_fixture(root: Path, *, mutate: object | None = None) -> None:
    registry = json.loads(
        (ROOT / "sources" / "registry.json").read_text(encoding="utf-8")
    )
    policy = json.loads(
        (ROOT / "config" / "campaign-policy.json").read_text(encoding="utf-8")
    )
    policy["source_groups"] = {
        name: policy["source_groups"][name]
        for name in (
            "openai-format-authority",
            "github-delivery",
            "python-packaging",
        )
    }
    policy["source_groups"]["openai-format-authority"]["source_ids"].remove(
        "openai-plugin-catalog"
    )
    policy["canary_source_ids"] = [
        "openai-build-skills",
        "github-cli-release-view",
        "pypi-updates",
    ]
    if mutate is not None:
        mutate(policy)
    write_registry(root, registry["sources"])
    (root / "config").mkdir()
    (root / "config" / "campaign-policy.json").write_text(
        json.dumps(policy, indent=2) + "\n", encoding="utf-8"
    )
    (root / "catalog").mkdir()
    (root / "catalog" / "capabilities.json").write_text(
        (ROOT / "catalog" / "capabilities.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


class CampaignTests(unittest.TestCase):
    def test_healthy_canary_automatically_ramps_to_registered_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_campaign_fixture(root)
            fetcher = MappingFetcher()

            report = run_campaign(
                root,
                fetcher,
                now="2026-08-29T05:00:00Z",
                ramp=True,
            )

            self.assertEqual(report["status"], "changed")
            self.assertTrue(report["ramped"])
            self.assertEqual(report["registered_endpoints"], 26)
            self.assertEqual(report["canary_endpoints"], 3)
            self.assertEqual(report["metrics"]["source_requests"], 26)
            self.assertGreater(report["metrics"]["downloaded_bytes"], 0)
            self.assertEqual(report["metrics"]["normalized_candidates"], 0)
            self.assertEqual(report["metrics"]["deep_reviews"], {"measured": False})
            self.assertEqual(report["metrics"]["usage_credits"], {"measured": False})
            self.assertEqual(report["metrics"]["observations_inserted"], 26)
            self.assertEqual(report["metrics"]["failures"], 0)
            persisted = json.loads(
                (root / "runs" / "2026-08-29T05-00-00Z-campaign.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(persisted, report)
            self.assertEqual(list((root / "runs").glob("*-scan.json")), [])
            self.assertEqual(list((root / "runs").glob("*-scan.md")), [])

    def test_campaign_accepts_additional_source_groups_without_a_code_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_campaign_fixture(
                root,
                mutate=lambda policy: policy["source_groups"].update(
                    {
                        "plugin-examples": {
                            "topic_id": "software.discover.plugin-examples",
                            "source_ids": ["openai-plugin-catalog"],
                        }
                    }
                ),
            )

            report = run_campaign(
                root,
                MappingFetcher(),
                now="2026-08-29T05:30:00Z",
                ramp=True,
            )

            self.assertEqual(report["registered_endpoints"], 27)
            source = next(
                run["sources"][0]
                for run in report["runs"]
                if run["sources"][0]["source_id"] == "openai-plugin-catalog"
            )
            self.assertEqual(source["source_group"], "plugin-examples")
            self.assertEqual(
                source["topic_id"], "software.discover.plugin-examples"
            )

    def test_failed_ramp_keeps_a_checkpoint_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_campaign_fixture(
                root,
                mutate=lambda policy: policy["source_groups"][
                    "openai-format-authority"
                ]["source_ids"].append("openai-plugin-catalog"),
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
            self.assertIn("HTTP 403", report["failure"]["error"])
            self.assertEqual(report["failure"]["phase"], "ramp")
            self.assertTrue(report["checkpoint"]["completed_source_ids"])
            self.assertTrue((root / "runs" / "2026-08-29T06-00-00Z-campaign.json").is_file())
            self.assertEqual(
                list((root / "runs").glob("*-scan-failed.json")), []
            )

    def test_canary_failure_also_writes_a_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_campaign_fixture(root)

            report = run_campaign(
                root,
                FailingCanaryFetcher(),
                now="2026-08-29T06:10:00Z",
                ramp=True,
            )

            self.assertEqual(report["status"], "checkpoint")
            self.assertIn("canary source failure", report["stop_reasons"])
            self.assertEqual(report["failure"]["phase"], "canary")
            self.assertEqual(report["metrics"]["failures"], 1)
            self.assertTrue(
                (root / "runs" / "2026-08-29T06-10-00Z-campaign.json").is_file()
            )

    def test_request_byte_and_store_stop_loss_checkpoint_before_more_work(self) -> None:
        cases = (
            (
                "requests",
                lambda policy: policy["stop_loss"].update(max_source_requests=1),
                "max_source_requests reached",
                1,
            ),
            (
                "bytes",
                lambda policy: policy["stop_loss"].update(max_download_bytes=10),
                "max_download_bytes reached",
                1,
            ),
            (
                "store",
                lambda policy: policy["stop_loss"].update(max_runtime_store_bytes=1),
                "max_runtime_store_bytes reached",
                0,
            ),
        )
        for index, (label, mutate, reason, expected_requests) in enumerate(cases):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                write_campaign_fixture(root, mutate=mutate)

                report = run_campaign(
                    root,
                    MappingFetcher(),
                    now=f"2026-08-29T07:0{index}:00Z",
                    ramp=True,
                )

                self.assertEqual(report["status"], "checkpoint")
                self.assertIn(reason, report["stop_reasons"])
                self.assertEqual(
                    report["metrics"]["source_requests"], expected_requests
                )
                self.assertTrue(report["checkpoint"]["pending_source_ids"])

    def test_changed_pypi_feed_keeps_campaign_truthfully_changed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_campaign_fixture(root)

            first = run_campaign(
                root,
                ChangingPyPIFetcher("package-one"),
                now="2026-08-29T07:10:00Z",
                ramp=True,
            )
            second = run_campaign(
                root,
                ChangingPyPIFetcher("package-two"),
                now="2026-08-29T07:11:00Z",
                ramp=True,
            )

            self.assertEqual(first["status"], "changed")
            self.assertEqual(second["status"], "changed")
            self.assertEqual(second["metrics"]["observations_inserted"], 1)
            self.assertEqual(second["metrics"]["normalized_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
