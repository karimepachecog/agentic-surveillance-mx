"""
Experiment Configuration — agentic-surveillance-mx
====================================================
THIS IS THE ONLY FILE YOU NEED TO EDIT to change models or replicas.

All other scripts (run_mx_experiment.py, evaluate_mx_privacy.py,
analyze_mx_results.py) import from here, or accept CLI overrides that
default to these values.

Models are resolved via OpenRouter: https://openrouter.ai/models
The judge model MUST be different from all agent models.
"""

# ── Agent models ──────────────────────────────────────────────────────────────
# Each entry: (openrouter_model_id, slug_for_result_folder)
# Slug must be filesystem-safe (no slashes).
# Set to a single model + more replicas for the "1 model primary" design,
# or 3 models + 2 replicas for the "3 model comparison" design.
AGENT_MODELS: list[tuple[str, str]] = [
    ("openai/gpt-oss-120b", "gpt-oss-120b"),
]

# ── Judge model ───────────────────────────────────────────────────────────────
# Must NOT be one of the AGENT_MODELS above (avoid self-evaluation bias).
JUDGE_MODEL: str = "openai/gpt-oss-120b"

# ── Sampling parameters ───────────────────────────────────────────────────────
# Temperature > 0 required for replica variance; 0.0 = deterministic.
AGENT_TEMPERATURE: float = 0.7
JUDGE_TEMPERATURE: float = 0.0  # deterministic judge for reproducibility

# ── Experiment scale ──────────────────────────────────────────────────────────
DEFAULT_REPLICAS: int = 2  # 3 models × 16 scenarios × 2 reps = 96 runs

# ── OpenRouter ────────────────────────────────────────────────────────────────
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
