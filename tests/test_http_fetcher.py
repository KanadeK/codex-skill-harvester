from __future__ import annotations

import sys
import subprocess
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.sources import GitHubCliFetcher, SourceFetchError, UrllibFetcher


class FakeResponse:
    def __init__(self, body: bytes, final_url: str = "https://example.test/final") -> None:
        self.status = 200
        self.headers = {"ETag": '"v1"'}
        self.body = body
        self.final_url = final_url

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def geturl(self) -> str:
        return self.final_url


class HttpFetcherTests(unittest.TestCase):
    @patch("skill_harvester.sources.urlopen")
    def test_fetches_with_bounded_read_and_normalized_headers(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(b"evidence")

        response = UrllibFetcher(max_bytes=100).fetch(
            "https://example.test/source", {"If-None-Match": '"old"'}
        )

        self.assertEqual(response.body, b"evidence")
        self.assertEqual(response.headers["etag"], '"v1"')
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("If-none-match"), '"old"')
        self.assertIn("codex-skill-harvester", request.get_header("User-agent"))

    @patch("skill_harvester.sources.urlopen")
    def test_github_token_is_sent_only_to_the_github_api(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(b"evidence", final_url="https://api.github.com/final")
        fetcher = UrllibFetcher(github_token="secret-test-token")

        fetcher.fetch("https://api.github.com/search/repositories", {})
        github_request = urlopen.call_args.args[0]
        self.assertEqual(github_request.get_header("Authorization"), "Bearer secret-test-token")

        urlopen.return_value = FakeResponse(b"evidence")
        fetcher.fetch("https://example.test/source", {})
        other_request = urlopen.call_args.args[0]
        self.assertIsNone(other_request.get_header("Authorization"))

    @patch("skill_harvester.sources.subprocess.run")
    def test_github_cli_fetcher_uses_official_gh_without_exporting_a_token(self, run: object) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = b'{"items": []}'
        run.return_value.stderr = b""
        fetcher = GitHubCliFetcher()

        response = fetcher.fetch(
            "https://api.github.com/search/repositories?q=agent-skills",
            {"Accept": "application/json", "If-None-Match": '"old"'},
        )

        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b'{"items": []}')
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["gh", "api", "--method"])
        self.assertNotIn("Authorization", " ".join(command))

    @patch("skill_harvester.sources.subprocess.run")
    def test_github_cli_fetcher_rejects_response_larger_than_limit(self, run: object) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = b"12345"
        run.return_value.stderr = b""

        with self.assertRaisesRegex(SourceFetchError, "size limit"):
            GitHubCliFetcher(max_response_bytes=4).fetch(
                "https://api.github.com/repos/openai/plugins/contents/plugins",
                {"Accept": "application/json"},
            )

    @patch("skill_harvester.sources.subprocess.run")
    def test_github_cli_fetcher_reports_timeout(self, run: object) -> None:
        run.side_effect = subprocess.TimeoutExpired(["gh", "api"], timeout=1)

        with self.assertRaisesRegex(SourceFetchError, "timed out"):
            GitHubCliFetcher(timeout=1).fetch(
                "https://api.github.com/repos/openai/plugins/contents/plugins",
                {"Accept": "application/json"},
            )

    @patch("skill_harvester.sources.urlopen")
    def test_rejects_response_larger_than_limit(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(b"12345")

        with self.assertRaisesRegex(SourceFetchError, "size limit"):
            UrllibFetcher(max_bytes=4).fetch("https://example.test/source", {})

    @patch("skill_harvester.sources.urlopen")
    def test_returns_conditional_not_modified_response(self, urlopen: object) -> None:
        headers = Message()
        headers["ETag"] = '"same"'
        urlopen.side_effect = HTTPError(
            "https://example.test/source", 304, "Not Modified", headers, None
        )

        response = UrllibFetcher().fetch("https://example.test/source", {})

        self.assertEqual(response.status, 304)
        self.assertEqual(response.headers["etag"], '"same"')
        self.assertEqual(response.body, b"")

    @patch("skill_harvester.sources.urlopen")
    def test_rejects_redirect_to_non_https_url(self, urlopen: object) -> None:
        urlopen.return_value = FakeResponse(b"evidence", final_url="http://example.test/final")

        with self.assertRaisesRegex(SourceFetchError, "redirected outside https"):
            UrllibFetcher().fetch("https://example.test/source", {})


if __name__ == "__main__":
    unittest.main()
