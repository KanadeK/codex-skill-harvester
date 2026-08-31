from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.evals import run_eval_file


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "api-request-safety"
    / "skills"
    / "audit-curl-request"
    / "scripts"
    / "inspect_curl_request.py"
)


class CurlRequestSkillTests(unittest.TestCase):
    def run_script(
        self,
        value: object,
        *,
        config_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            input_path = temporary / "request.json"
            input_path.write_text(json.dumps(value), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), "--input", str(input_path)]
            if config_text is not None:
                config_path = temporary / "curl.conf"
                config_path.write_text(config_text, encoding="utf-8")
                command.extend(["--config", str(config_path)])
            return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_safe_post_is_reviewable_without_network(self) -> None:
        completed = self.run_script(
            {
                "arguments": [
                    "--disable",
                    "--request",
                    "POST",
                    "--data-urlencode",
                    "name=hello world",
                    "https://api.example.invalid/items",
                ],
                "intent": {"method": "POST"},
            }
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["status"], "reviewable")
        self.assertEqual(payload["request"]["method"], "POST")
        self.assertEqual(payload["request"]["url_count"], 1)
        self.assertFalse(payload["protections"]["network_executed"])

    def test_request_head_without_head_mode_is_blocked(self) -> None:
        completed = self.run_script(
            {
                "arguments": [
                    "--disable",
                    "--request",
                    "HEAD",
                    "https://api.example.invalid/health",
                ]
            }
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("request-head-without-head-mode", [item["code"] for item in payload["findings"]])

    def test_credentials_and_file_references_are_redacted_and_blocked(self) -> None:
        completed = self.run_script(
            {
                "arguments": [
                    "--disable",
                    "--data",
                    "@private-payload.txt",
                    "--header",
                    "Authorization: Bearer secret-value",
                    "https://api.example.invalid/items",
                ]
            }
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["request"]["file_reference_options"], ["--data"])
        self.assertEqual(payload["request"]["credential_options"], ["--header"])
        self.assertNotIn("private-payload.txt", completed.stdout)
        self.assertNotIn("secret-value", completed.stdout)
        self.assertFalse(payload["protections"]["referenced_files_read"])

    def test_explicit_config_is_parsed_without_loading_default_config(self) -> None:
        completed = self.run_script(
            {"arguments": ["--disable"], "intent": {"method": "POST"}},
            config_text=(
                'url = "https://api.example.invalid/items"\n'
                "request = POST\n"
                'data-urlencode = "name=hello world"\n'
            ),
        )
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["status"], "reviewable")
        self.assertEqual(payload["request"]["method"], "POST")
        self.assertTrue(payload["request"]["explicit_config_inspected"])

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT, ROOT / "evals" / "audit-curl-request.json", Path(directory)
            )

        self.assertEqual(report["trigger_cases"], 8)
        self.assertEqual(report["e2e_result"], "blocked")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
