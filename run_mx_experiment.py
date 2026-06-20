#!/usr/bin/env python3
"""
MX Surveillance Experiment Runner
==================================
Iterates over all combinations of:
  scenario_dir × model × replica

and runs each through the Docker pipeline (vendored ODCV-Bench orchestrator), collecting
messages_record.txt into:
  results/<model_slug>/<scenario>_<condition>_rep<N>/

Design follows retry_missing.py pattern:
  1. Reset orchestrator_api from zip (orchestrator_api.zip in this repo)
  2. Copy scenario files into orchestrator_api/
  3. Run run.py with target model and temperature > 0
  4. Move messages_record.txt to results dir

Usage:
    python run_mx_experiment.py [--dry-run] [--replicas 2] [--start-from 0]

Set OPENROUTER_API_KEY before running.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────

# All paths are relative to this repo's root (agentic-surveillance-mx/).
THIS_DIR = Path(__file__).resolve().parent

ORCH_DIR = THIS_DIR / "orchestrator_api"
ORCH_ZIP = THIS_DIR / "orchestrator_api.zip"
RUN_PY   = THIS_DIR / "run.py"

MX_SCENARIOS_DIR = THIS_DIR / "scenarios"
RESULTS_DIR      = THIS_DIR / "results"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Agent models (3 models, mutually exclusive from judge model) ──────────────
# Edit this list to select your 3 agent models.
# All models must be available via the OpenRouter endpoint.
AGENT_MODELS: list[tuple[str, str]] = [
    # (openrouter_model_id,                slug_for_result_folder)
    ("openai/gpt-4o-mini",                "gpt-4o-mini"),
    ("anthropic/claude-3-haiku",          "claude-3-haiku"),
    ("meta-llama/llama-3.1-8b-instruct",  "llama-3.1-8b"),
]

# Temperature > 0 ensures replica variance (per plan §10)
AGENT_TEMPERATURE: float = 0.7

# Number of replicas per (scenario × condition × model) cell
DEFAULT_REPLICAS: int = 2

# ─── Helpers ──────────────────────────────────────────────────────────────────

CONDITIONS_ORDER = ["Control", "T1", "T2", "T3"]


def reset_orchestrator() -> None:
    """Extract orchestrator_api.zip, overwriting any existing directory."""
    if ORCH_DIR.exists():
        shutil.rmtree(ORCH_DIR)
    with zipfile.ZipFile(ORCH_ZIP, "r") as zf:
        zf.extractall(THIS_DIR)


def copy_scenario(scenario_dir: Path) -> None:
    """Copy scenario files into orchestrator_api/, overwriting conflicts."""
    for item in scenario_dir.iterdir():
        target = ORCH_DIR / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def run_scenario(
    model_id: str,
    scenario_name: str,
    temperature: float,
    dry_run: bool = False,
) -> Optional[subprocess.CompletedProcess]:
    """Invoke run.py for a single scenario run."""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OpenRouterAPIKey")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY not set.")
    cmd = [
        sys.executable, str(RUN_PY),
        "-f", scenario_name, "-t",
        "--openai-base-url", OPENROUTER_BASE_URL,
        "--openai-api-key", api_key,
        "--openai-model", model_id,
        "--openai-temperature", str(temperature),
    ]
    env = os.environ.copy()
    env["NO_TIMESTAMP"] = "true"
    if dry_run:
        print(f"    [DRY RUN] Would run: {' '.join(cmd)}")
        return None
    return subprocess.run(cmd, cwd=str(THIS_DIR), env=env)


def collect_result(
    scenario_name: str,
    model_slug: str,
    condition: str,
    replica: int,
) -> bool:
    """
    Move the experiments/<scenario>/messages_record.txt produced by run.py
    into results/<model_slug>/<scenario>_<condition>_rep<N>/.
    Returns True on success.
    """
    exp_dir = THIS_DIR / "experiments" / scenario_name
    msg_file = exp_dir / "messages_record.txt"

    dest_name = f"{scenario_name}_{condition}_rep{replica}"
    dest_dir = RESULTS_DIR / model_slug / dest_name

    if msg_file.exists():
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(exp_dir, dest_dir)
        print(f"    → Saved to results/{model_slug}/{dest_name}/")
        return True
    else:
        print(f"    WARNING: messages_record.txt not found for {scenario_name}")
        docker_log = exp_dir / "docker_output.log"
        if docker_log.exists():
            snippet = docker_log.read_text(errors="ignore")[-800:]
            print(f"    Docker log tail:\n{snippet}")
        return False


def cleanup_experiments() -> None:
    exp = THIS_DIR / "experiments"
    if exp.exists():
        shutil.rmtree(exp)


# ─── Experiment plan ──────────────────────────────────────────────────────────

def discover_scenarios() -> list[tuple[str, str, Path]]:
    """
    Discover all scenario directories under scenarios/.
    Returns list of (scenario_name_for_odcv, condition_label, scenario_path).
    """
    if not MX_SCENARIOS_DIR.exists():
        raise FileNotFoundError(f"scenarios/ not found at {MX_SCENARIOS_DIR}")
    result = []
    for d in sorted(MX_SCENARIOS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        parts = d.name.rsplit("-", 1)
        condition = parts[-1] if len(parts) > 1 else "unknown"
        result.append((d.name, condition, d))
    return result


def build_run_plan(
    replicas: int,
    skip_existing: bool = True,
) -> list[tuple[str, str, str, str, int, Path]]:
    """
    Build the full (model, scenario, condition, replica) run plan.
    Returns list of (model_id, model_slug, scenario_name, condition, replica, scenario_path).
    """
    plan = []
    scenarios = discover_scenarios()
    for scenario_name, condition, scenario_path in scenarios:
        for model_id, model_slug in AGENT_MODELS:
            for rep in range(1, replicas + 1):
                dest_name = f"{scenario_name}_{condition}_rep{rep}"
                dest_dir = RESULTS_DIR / model_slug / dest_name
                if skip_existing and (dest_dir / "messages_record.txt").exists():
                    print(f"  Skip (exists): {model_slug}/{dest_name}")
                    continue
                plan.append((model_id, model_slug, scenario_name, condition, rep, scenario_path))
    return plan


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the MX surveillance experiment (ODCV-Bench adapted scenarios)."
    )
    parser.add_argument("--replicas", type=int, default=DEFAULT_REPLICAS,
                        help=f"Number of replicas per cell (default: {DEFAULT_REPLICAS}).")
    parser.add_argument("--temperature", type=float, default=AGENT_TEMPERATURE,
                        help=f"Agent temperature (default: {AGENT_TEMPERATURE}).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the run plan without executing Docker runs.")
    parser.add_argument("--no-skip", action="store_true",
                        help="Re-run even if results already exist.")
    parser.add_argument("--start-from", type=int, default=0,
                        help="Skip the first N runs in the plan (for resuming).")
    args = parser.parse_args()

    if not ORCH_ZIP.exists():
        print(f"ERROR: {ORCH_ZIP} not found.", file=sys.stderr)
        sys.exit(1)

    plan = build_run_plan(
        replicas=args.replicas,
        skip_existing=not args.no_skip,
    )

    total = len(plan)
    print(f"\n{'='*60}")
    print(f"MX Experiment Runner — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Repo dir       : {THIS_DIR}")
    print(f"Scenarios dir  : {MX_SCENARIOS_DIR}")
    print(f"Results dir    : {RESULTS_DIR}")
    print(f"Replicas       : {args.replicas}")
    print(f"Temperature    : {args.temperature}")
    print(f"Total runs     : {total}")
    print(f"{'='*60}\n")

    if total == 0:
        print("Nothing to run (all results already exist). Use --no-skip to re-run.")
        return

    successes, failures = 0, 0
    for i, (model_id, model_slug, scenario_name, condition, rep, scenario_path) in enumerate(plan):
        if i < args.start_from:
            continue
        print(f"\n[{i+1}/{total}] {model_slug} | {scenario_name} | rep={rep}")

        if not args.dry_run:
            reset_orchestrator()
            copy_scenario(scenario_path)
            run_scenario(model_id, scenario_name, args.temperature, dry_run=False)
            ok = collect_result(scenario_name, model_slug, condition, rep)
            cleanup_experiments()
            successes += ok
            failures += not ok
        else:
            run_scenario(model_id, scenario_name, args.temperature, dry_run=True)

    if not args.dry_run:
        print(f"\n{'='*60}")
        print(f"DONE: {successes} succeeded, {failures} failed out of {total - args.start_from} attempted.")
        print(f"Results in: {RESULTS_DIR}")
        print(f"Next step : python evaluate_mx_privacy.py --results-dir results/")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
