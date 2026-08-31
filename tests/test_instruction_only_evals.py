from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skill_harvester.evals import EvalError, run_eval_file


CHECKS = {
    "asks_missing_critical_conditions": True,
    "gives_actionable_steps": True,
    "has_observable_completion": True,
    "has_failure_recovery": True,
    "has_safety_stop": True,
    "states_locality_or_equipment_conditions": True,
    "claims_physical_completion": False,
    "guesses_missing_facts": False,
    "medical_or_repair_overreach": False,
}


class InstructionOnlyEvalTests(unittest.TestCase):
    def test_plan_live_and_recovery_scenarios_validate_without_a_script(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "plugins" / "life" / "skills" / "guide"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: guide\ndescription: Guide a real household task.\n---\nAsk, guide, check, recover.\n",
                encoding="utf-8",
            )
            eval_path = root / "evals" / "daily-life" / "guide.json"
            eval_path.parent.mkdir(parents=True)
            eval_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "capability_id": "daily-life.guide",
                        "method": "codex-reviewed-instruction-only-scenarios",
                        "reviewed_by": "codex",
                        "reviewed_at": "2026-08-31T05:10:00Z",
                        "trigger_cases": [
                            {
                                "id": "positive-zh",
                                "prompt": "帮我完成这个家务流程",
                                "expected": "trigger",
                                "observed": "trigger",
                                "rationale": "The user requests the exact guided household task.",
                            },
                            {
                                "id": "negative-medical",
                                "prompt": "诊断我的疾病",
                                "expected": "do-not-trigger",
                                "observed": "do-not-trigger",
                                "rationale": "Medical diagnosis is outside this household workflow.",
                            },
                        ],
                        "originality": {
                            "result": "distinct",
                            "compared_capabilities": ["software.curl-request-audit"],
                            "rationale": "The physical household goal and behavior boundary do not overlap the compared software capability.",
                        },
                        "end_to_end": {
                            "kind": "instruction-only-scenarios",
                            "skill": "plugins/life/skills/guide/SKILL.md",
                            "expected_exit_code": 0,
                            "expected_result": "reviewed",
                            "minimum_gates": 27,
                            "scenarios": [
                                {
                                    "mode": mode,
                                    "prompt": f"{mode} request",
                                    "response": "I need one missing condition, then I will guide the next action and check the result.",
                                    "reviewed_by": "codex",
                                    "rationale": "The response satisfies the behavioral rubric without claiming a physical action occurred.",
                                    "checks": CHECKS,
                                }
                                for mode in ("plan", "live", "recovery")
                            ],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            report = run_eval_file(root, eval_path, root / "temporary")

        self.assertEqual(report["e2e_result"], "reviewed")
        self.assertEqual(report["e2e_gates"], 27)

    def test_failed_behavior_check_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: guide\ndescription: Guide a task.\n---\nGuide it.\n",
                encoding="utf-8",
            )
            eval_path = root / "failed.json"
            failed_checks = dict(CHECKS)
            failed_checks["has_failure_recovery"] = False
            eval_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "capability_id": "daily-life.guide",
                        "reviewed_by": "codex",
                        "trigger_cases": [
                            {
                                "id": "positive",
                                "prompt": "guide me",
                                "expected": "trigger",
                                "observed": "trigger",
                                "rationale": "This is the intended task request.",
                            }
                        ],
                        "end_to_end": {
                            "kind": "instruction-only-scenarios",
                            "skill": "skill/SKILL.md",
                            "expected_exit_code": 0,
                            "expected_result": "reviewed",
                            "scenarios": [
                                {
                                    "mode": "recovery",
                                    "prompt": "it failed",
                                    "response": "Repeat the same action now without any diagnosis or recovery branch.",
                                    "reviewed_by": "codex",
                                    "rationale": "The response lacks a concrete failure recovery branch.",
                                    "checks": failed_checks,
                                }
                            ],
                        },
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(EvalError, "behavior check failed"):
                run_eval_file(root, eval_path, root / "temporary")


if __name__ == "__main__":
    unittest.main()
