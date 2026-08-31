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
    / "web-request-diagnostics"
    / "skills"
    / "diagnose-cors-request"
    / "scripts"
    / "classify_cors.py"
)


def evidence() -> dict[str, object]:
    return {
        "page_origin": "https://app.example",
        "request": {
            "url": "https://api.example/items",
            "method": "POST",
            "mode": "cors",
            "credentials": "include",
            "headers": {"content-type": "application/json", "x-request-id": "redacted"},
        },
        "preflight": {
            "status": 204,
            "headers": {
                "access-control-allow-origin": "https://app.example",
                "access-control-allow-credentials": "true",
                "access-control-allow-methods": "POST",
                "access-control-allow-headers": "content-type, x-request-id",
            },
        },
        "response": {
            "status": 200,
            "headers": {
                "access-control-allow-origin": "https://app.example",
                "access-control-allow-credentials": "true",
            },
        },
    }


class CorsDiagnosticsSkillTests(unittest.TestCase):
    def run_script(self, value: object) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_allows_complete_credentialed_preflight(self) -> None:
        completed = self.run_script(evidence())
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(payload["status"], "allowed")
        self.assertTrue(payload["preflight_required"])

    def test_blocks_wildcard_origin_with_credentials(self) -> None:
        value = evidence()
        value["response"]["headers"]["access-control-allow-origin"] = "*"
        completed = self.run_script(value)
        payload = json.loads(completed.stdout)

        self.assertEqual(completed.returncode, 1)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("wildcard", " ".join(payload["findings"]))

    def test_missing_preflight_and_no_cors_are_not_false_success(self) -> None:
        missing = evidence()
        missing.pop("preflight")
        incomplete = self.run_script(missing)
        self.assertEqual(incomplete.returncode, 1)
        self.assertEqual(json.loads(incomplete.stdout)["status"], "unverified")

        opaque = evidence()
        opaque["request"]["mode"] = "no-cors"
        no_cors = self.run_script(opaque)
        self.assertEqual(no_cors.returncode, 1)
        self.assertEqual(json.loads(no_cors.stdout)["status"], "opaque")

    def test_reviewed_triggers_originality_and_e2e_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = run_eval_file(
                ROOT, ROOT / "evals" / "diagnose-cors-request.json", Path(directory)
            )

        self.assertEqual(report["trigger_cases"], 7)
        self.assertEqual(report["e2e_result"], "blocked")
        self.assertEqual(report["originality"], "distinct")


if __name__ == "__main__":
    unittest.main()
