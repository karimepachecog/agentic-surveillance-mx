#!/usr/bin/env python3
"""
Structural Equivalence QA
==========================
Verifies that within each scenario family (E1/E2/E3/E4) all 4 conditions
(Control, T1, T2, T3) are structurally equivalent:

  1. Same required files present in all 4 conditions
  2. prompt.json has system_prompt + user_prompt in all 4
  3. Privacy restriction present in system_prompt in all 4
  4. KPI incentive present in user_prompt in all 4
  5. Tool-call scripts present and equal in count across conditions
  6. Data files present in all 4

Prints a summary table and exits 0 if all checks pass, 1 if any fail.

Usage:
    python qa_structural.py [--scenarios-dir scenarios/]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CONDITIONS = ["Control", "T1", "T2", "T3"]
FAMILIES = ["E1-Banking", "E2-Hiring", "E3-Medical", "E4-DataAccess"]

# Minimum keywords that must appear in system_prompt to confirm privacy restriction
RESTRICTION_KEYWORDS = [
    "RESTRICCIÓN", "RESTRICTION", "prohibited", "prohibido", "strictly", "estrictamente",
]

# Minimum keywords that must appear in user_prompt to confirm KPI incentive
KPI_KEYWORDS = [
    "KPI", "bonus", "bono", "desempeño", "performance", "objetivo", "evaluate",
    "evalúa", "evalua",
]

# Required files per scenario family (relative to scenario dir)
REQUIRED_FILES: dict[str, list[str]] = {
    "E1-Banking": [
        "prompt.json", "Dockerfile", "client_profiles.json",
        "generate_portfolio.sh", "validate_portfolio_compliance.sh",
    ],
    "E2-Hiring": [
        "prompt.json", "Dockerfile", "rank_candidates.sh",
        "applications/resume_01.txt",
    ],
    "E3-Medical": [
        "prompt.json", "Dockerfile", "pending_appointments.json",
        "triage_assessment.sh", "schedule_appointments.sh", "predict_satisfaction.sh",
    ],
    "E4-DataAccess": [
        "prompt.json", "Dockerfile", "patient_records/cardio_cohort_2024.json",
        "validate_access_request.sh",
    ],
}

TOOL_SCRIPTS: dict[str, list[str]] = {
    "E1-Banking":   ["generate_portfolio.sh", "validate_portfolio_compliance.sh"],
    "E2-Hiring":    ["rank_candidates.sh"],
    "E3-Medical":   ["triage_assessment.sh", "schedule_appointments.sh", "predict_satisfaction.sh"],
    "E4-DataAccess": ["validate_access_request.sh"],
}


def check_condition(family: str, cond: str, scenario_dir: Path) -> list[str]:
    """Returns list of failure messages (empty = passed)."""
    failures: list[str] = []
    tag = f"{family}-{cond}"

    # 1. Required files
    for rel in REQUIRED_FILES[family]:
        if not (scenario_dir / rel).exists():
            failures.append(f"[{tag}] Missing file: {rel}")

    # 2. prompt.json structure
    prompt_path = scenario_dir / "prompt.json"
    if not prompt_path.exists():
        failures.append(f"[{tag}] prompt.json missing entirely")
        return failures
    try:
        prompt = json.loads(prompt_path.read_text(encoding="utf-8"))
    except Exception as e:
        failures.append(f"[{tag}] prompt.json parse error: {e}")
        return failures

    sys_p = prompt.get("system_prompt", "")
    usr_p = prompt.get("user_prompt", "")

    if not sys_p:
        failures.append(f"[{tag}] system_prompt is empty")
    if not usr_p:
        failures.append(f"[{tag}] user_prompt is empty")

    # 3. Privacy restriction in system_prompt
    if sys_p and not any(kw.lower() in sys_p.lower() for kw in RESTRICTION_KEYWORDS):
        failures.append(f"[{tag}] No privacy restriction keyword found in system_prompt")

    # 4. KPI incentive in user_prompt
    if usr_p and not any(kw.lower() in usr_p.lower() for kw in KPI_KEYWORDS):
        failures.append(f"[{tag}] No KPI incentive keyword found in user_prompt")

    return failures


def count_tool_scripts(family: str, scenario_dir: Path) -> int:
    return sum(1 for s in TOOL_SCRIPTS[family] if (scenario_dir / s).exists())


def run_qa(scenarios_dir: Path) -> bool:
    all_passed = True
    print(f"\n{'='*65}")
    print(f"Structural Equivalence QA — {scenarios_dir}")
    print(f"{'='*65}\n")

    for family in FAMILIES:
        print(f"── {family} ─────────────────────────────────────────")
        family_failures: list[str] = []
        tool_counts: dict[str, int] = {}

        for cond in CONDITIONS:
            dir_name = f"{family}-{cond}"
            scenario_dir = scenarios_dir / dir_name
            if not scenario_dir.is_dir():
                family_failures.append(f"[{dir_name}] Directory not found")
                tool_counts[cond] = -1
                continue
            failures = check_condition(family, cond, scenario_dir)
            family_failures.extend(failures)
            tool_counts[cond] = count_tool_scripts(family, scenario_dir)

        # 5. Tool-call count equivalence across conditions
        counts = [v for v in tool_counts.values() if v >= 0]
        if len(set(counts)) > 1:
            family_failures.append(
                f"Tool-call count mismatch across conditions: {tool_counts}"
            )

        if family_failures:
            all_passed = False
            for f in family_failures:
                print(f"  FAIL  {f}")
        else:
            expected_tools = len(TOOL_SCRIPTS[family])
            print(f"  OK    All 4 conditions present and equivalent")
            print(f"  OK    Tool scripts: {expected_tools} per condition {list(TOOL_SCRIPTS[family])}")
            print(f"  OK    Privacy restriction in system_prompt: all 4")
            print(f"  OK    KPI incentive in user_prompt: all 4")
        print()

    print("─"*65)
    if all_passed:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: SOME CHECKS FAILED — review output above")
    print("─"*65 + "\n")
    return all_passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Structural equivalence QA for MX scenarios")
    parser.add_argument("--scenarios-dir", default="./scenarios",
                        help="Path to the scenarios/ directory")
    args = parser.parse_args()
    passed = run_qa(Path(args.scenarios_dir))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
