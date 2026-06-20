#!/usr/bin/env python3
"""
Infrastructure preflight check for the MX surveillance experiment.

Verifies:
  1. Docker and Docker Compose are available and running
  2. OPENROUTER_API_KEY is set (and optionally pings the API)
  3. orchestrator_api.zip is present in this repo and extractable
  4. All 16 scenarios/ directories exist with required files
  5. Python dependencies for analysis are installed

Usage:
    python check_mx_infra.py [--ping-api]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from experiment_config import AGENT_MODELS, JUDGE_MODEL, DEFAULT_REPLICAS

THIS_DIR   = Path(__file__).resolve().parent
ORCH_ZIP   = THIS_DIR / "orchestrator_api.zip"
SCENARIOS  = THIS_DIR / "scenarios"

REQUIRED_FILES: dict[str, list[str]] = {
    "E1-Banking-Control":    ["prompt.json", "client_profiles.json", "generate_portfolio.sh",
                               "validate_portfolio_compliance.sh", "Dockerfile"],
    "E1-Banking-T1":         ["prompt.json", "client_profiles.json", "generate_portfolio.sh",
                               "validate_portfolio_compliance.sh", "Dockerfile"],
    "E1-Banking-T2":         ["prompt.json", "client_profiles.json", "generate_portfolio.sh",
                               "validate_portfolio_compliance.sh", "Dockerfile"],
    "E1-Banking-T3":         ["prompt.json", "client_profiles.json", "generate_portfolio.sh",
                               "validate_portfolio_compliance.sh", "Dockerfile"],
    "E2-Hiring-Control":     ["prompt.json", "rank_candidates.sh", "Dockerfile",
                               "applications/resume_01.txt"],
    "E2-Hiring-T1":          ["prompt.json", "rank_candidates.sh", "Dockerfile",
                               "applications/resume_01.txt"],
    "E2-Hiring-T2":          ["prompt.json", "rank_candidates.sh", "Dockerfile",
                               "applications/resume_01.txt"],
    "E2-Hiring-T3":          ["prompt.json", "rank_candidates.sh", "Dockerfile",
                               "applications/resume_01.txt"],
    "E3-Medical-Control":    ["prompt.json", "pending_appointments.json", "triage_assessment.sh",
                               "schedule_appointments.sh", "predict_satisfaction.sh", "Dockerfile"],
    "E3-Medical-T1":         ["prompt.json", "pending_appointments.json", "triage_assessment.sh",
                               "schedule_appointments.sh", "predict_satisfaction.sh", "Dockerfile"],
    "E3-Medical-T2":         ["prompt.json", "pending_appointments.json", "triage_assessment.sh",
                               "schedule_appointments.sh", "predict_satisfaction.sh", "Dockerfile"],
    "E3-Medical-T3":         ["prompt.json", "pending_appointments.json", "triage_assessment.sh",
                               "schedule_appointments.sh", "predict_satisfaction.sh", "Dockerfile"],
    "E4-DataAccess-Control": ["prompt.json", "patient_records/cardio_cohort_2024.json",
                               "validate_access_request.sh", "Dockerfile"],
    "E4-DataAccess-T1":      ["prompt.json", "patient_records/cardio_cohort_2024.json",
                               "validate_access_request.sh", "Dockerfile"],
    "E4-DataAccess-T2":      ["prompt.json", "patient_records/cardio_cohort_2024.json",
                               "validate_access_request.sh", "Dockerfile"],
    "E4-DataAccess-T3":      ["prompt.json", "patient_records/cardio_cohort_2024.json",
                               "validate_access_request.sh", "Dockerfile"],
}


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "✓ OK" if ok else "✗ FAIL"
    print(f"  [{status}] {name}" + (f"  → {detail}" if detail else ""))
    return ok


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="MX experiment preflight check")
    parser.add_argument("--ping-api", action="store_true")
    args = parser.parse_args()

    results: list[bool] = []
    print("\n" + "="*60)
    print("MX Experiment — Infrastructure Preflight Check")
    print("="*60 + "\n")

    # 1. Docker
    print("1. Docker")
    docker_ok = shutil.which("docker") is not None
    results.append(check("docker binary found", docker_ok))
    if docker_ok:
        try:
            out = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
            results.append(check("Docker daemon running", out.returncode == 0))
        except Exception as e:
            results.append(check("Docker daemon running", False, str(e)))
    compose_ok = (shutil.which("docker-compose") is not None or
                  subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0)
    results.append(check("Docker Compose available", compose_ok))
    print()

    # 2. API key
    print("2. OpenRouter API Key")
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OpenRouterAPIKey")
    key_set = bool(api_key)
    results.append(check("OPENROUTER_API_KEY set", key_set,
                         "export OPENROUTER_API_KEY=<your_key>" if not key_set else ""))
    if key_set and args.ping_api:
        try:
            from openai import OpenAI
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            resp = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": "Reply with OK only."}],
                max_tokens=5,
            )
            ping_ok = "ok" in (resp.choices[0].message.content or "").lower()
            results.append(check("API ping (gpt-4o-mini)", ping_ok))
        except Exception as e:
            results.append(check("API ping", False, str(e)))
    print()

    # 3. orchestrator_api.zip
    print(f"3. orchestrator_api.zip  ({ORCH_ZIP})")
    zip_exists = ORCH_ZIP.exists()
    results.append(check("orchestrator_api.zip found", zip_exists))
    if zip_exists:
        try:
            with zipfile.ZipFile(ORCH_ZIP, "r") as zf:
                names = zf.namelist()
            results.append(check("zip contains task_executor_api.py",
                                 any("task_executor_api.py" in n for n in names)))
            results.append(check("zip contains requirements.txt",
                                 any("requirements.txt" in n for n in names)))
        except Exception as e:
            results.append(check("zip is valid", False, str(e)))
    print()

    # 4. scenarios/ directories
    print("4. scenarios/ — 16 scenario directories")
    for scenario_name, required in sorted(REQUIRED_FILES.items()):
        d = SCENARIOS / scenario_name
        dir_ok = d.is_dir()
        missing = [f for f in required if not (d / f).exists()] if dir_ok else required
        results.append(check(
            f"  {scenario_name}", dir_ok and not missing,
            f"missing: {missing}" if missing else "",
        ))
    print()

    # 5. Experiment config
    print("5. experiment_config.py")
    print(f"  Agent models ({len(AGENT_MODELS)}):")
    for mid, slug in AGENT_MODELS:
        print(f"    {slug:<20}  {mid}")
    print(f"  Judge model  : {JUDGE_MODEL}")
    print(f"  Replicas     : {DEFAULT_REPLICAS}")
    total_runs = len(AGENT_MODELS) * DEFAULT_REPLICAS * 16
    print(f"  Total runs   : {len(AGENT_MODELS)} models × {DEFAULT_REPLICAS} reps × 16 scenarios = {total_runs}")
    results.append(check("experiment_config loaded", True))
    print()

    # 6. Python dependencies
    print("6. Python analysis dependencies")
    for pkg in ["scipy", "numpy", "matplotlib", "statsmodels", "openai"]:
        try:
            __import__(pkg)
            results.append(check(pkg, True))
        except ImportError:
            results.append(check(pkg, False, f"pip install {pkg}"))
    print()

    total = len(results)
    passed = sum(results)
    print("="*60)
    print(f"PREFLIGHT RESULT: {passed}/{total} checks passed")
    if passed == total:
        print("✓ All checks passed. Ready to run:")
        print("    cd agentic-surveillance-mx/")
        print("    python run_mx_experiment.py --dry-run")
    else:
        print(f"✗ {total - passed} check(s) failed. Fix issues above first.")
    print("="*60 + "\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
