from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

ML_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ML_ROOT / "config" / "training_config.json"
DATA_DIR = ML_ROOT / "data"


def load_training_config() -> Dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_synthetic_dataset(
    output_path: Path | None = None,
    n_samples: int | None = None,
    seed: int | None = None,
    missing_rate: float | None = None,
) -> Tuple[Path, pd.DataFrame, Dict]:
    """
    Generates a reproducible, clearly labelled synthetic demonstration dataset for the
    VYRO-X Adaptive Supervision Prediction Model.

    Labels are generated from a multi-factor latent supervision requirement combining
    task risk, task complexity, historical reliability/recovery, and interaction patterns
    with realistic boundary noise — never solely from approval or intervention counts.
    """
    cfg = load_training_config()
    n = n_samples if n_samples is not None else int(cfg["n_samples"])
    rng = np.random.default_rng(seed if seed is not None else int(cfg["random_seed"]))
    miss_rate = missing_rate if missing_rate is not None else float(cfg["missing_value_rate"])

    # Sample realistic diverse task & history profiles
    prev_approvals = rng.poisson(lam=8.0, size=n).astype(float)
    prev_rejections = rng.poisson(lam=1.6, size=n).astype(float)
    user_corrections = rng.poisson(lam=2.4, size=n).astype(float)
    interruptions_count = rng.poisson(lam=1.3, size=n).astype(float)
    manual_step_edits = rng.poisson(lam=2.1, size=n).astype(float)

    task_complexity = np.clip(rng.beta(2.2, 2.0, size=n), 0.05, 1.0)
    task_risk_level = rng.choice([0, 1, 2], size=n, p=[0.36, 0.40, 0.24]).astype(float)
    prev_completion_rate = np.clip(rng.beta(5.0, 1.6, size=n), 0.10, 1.0)
    historical_recovery_rate = np.clip(rng.beta(4.5, 1.5, size=n), 0.15, 1.0)

    # Intervention frequency correlates partially with corrections/interrupts plus independent variance
    base_interventions = (user_corrections + interruptions_count + prev_rejections) / np.maximum(
        1.0, (prev_approvals / 3.0) + 1.0
    )
    intervention_frequency = np.clip(base_interventions + rng.normal(0.0, 0.35, size=n), 0.0, 8.0)

    # Multi-factor non-linear latent supervision need score (higher => more human supervision needed)
    rejection_ratio = prev_rejections / (prev_approvals + prev_rejections + 1.0)
    reliability_deficit = (1.0 - prev_completion_rate) * 1.45 + (1.0 - historical_recovery_rate) * 1.15
    risk_complexity_interaction = (task_risk_level / 2.0) * (0.65 + 0.85 * task_complexity)
    friction_term = (
        0.55 * np.log1p(user_corrections + manual_step_edits)
        + 0.60 * np.log1p(interruptions_count)
        + 1.65 * rejection_ratio
        + 0.28 * intervention_frequency
    )
    # Experience stabilization (not blind trust: capped and outweighed by high risk or low reliability)
    experience_relief = 0.42 * np.log1p(prev_approvals) * prev_completion_rate * (1.0 - 0.35 * (task_risk_level == 2))

    # Realistic preference ambiguity noise
    noise = rng.normal(0.0, 0.28, size=n)
    latent_need = (
        1.35 * risk_complexity_interaction
        + 1.10 * reliability_deficit
        + 0.78 * friction_term
        - experience_relief
        + noise
    )

    # Calibrate thresholds for realistic class distribution (~28% supervised, ~46% balanced, ~26% higher_autonomy)
    q_low, q_high = np.quantile(latent_need, [0.26, 0.72])
    labels = np.where(
        latent_need >= q_high,
        "supervised",
        np.where(latent_need <= q_low, "higher_autonomy", "balanced"),
    )

    df = pd.DataFrame(
        {
            "prev_approvals": np.round(prev_approvals, 0),
            "prev_rejections": np.round(prev_rejections, 0),
            "user_corrections": np.round(user_corrections, 0),
            "interruptions_count": np.round(interruptions_count, 0),
            "manual_step_edits": np.round(manual_step_edits, 0),
            "task_complexity": np.round(task_complexity, 4),
            "task_risk_level": task_risk_level.astype(int),
            "prev_completion_rate": np.round(prev_completion_rate, 4),
            "intervention_frequency": np.round(intervention_frequency, 4),
            "historical_recovery_rate": np.round(historical_recovery_rate, 4),
            "target_autonomy": labels,
        }
    )

    # Inject controlled missingness into numeric features (excluding target & risk_level) to exercise imputation
    imputable_cols = [
        "prev_approvals",
        "prev_rejections",
        "user_corrections",
        "interruptions_count",
        "manual_step_edits",
        "task_complexity",
        "prev_completion_rate",
        "intervention_frequency",
        "historical_recovery_rate",
    ]
    for col in imputable_cols:
        mask = rng.random(size=n) < miss_rate
        df.loc[mask, col] = np.nan

    dest = output_path or (DATA_DIR / f"{cfg['dataset_version']}.csv")
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False)

    class_dist = {str(k): int(v) for k, v in df["target_autonomy"].value_counts().items()}
    meta = {
        "dataset_version": cfg["dataset_version"],
        "dataset_provenance": cfg["dataset_provenance"],
        "sample_count": int(len(df)),
        "class_distribution": class_dist,
        "missing_cells": int(df[imputable_cols].isna().sum().sum()),
        "sha256_hash": sha256_file(dest),
        "file_path": str(dest),
    }
    return dest, df, meta


if __name__ == "__main__":
    path, _df, meta = generate_synthetic_dataset()
    print(f"Generated synthetic dataset at {path}:")
    print(json.dumps(meta, indent=2))
