from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

REQUIRED_FEATURES = [
    "prev_approvals",
    "prev_rejections",
    "user_corrections",
    "interruptions_count",
    "manual_step_edits",
    "task_complexity",
    "task_risk_level",
    "prev_completion_rate",
    "intervention_frequency",
    "historical_recovery_rate",
]
VALID_CLASSES = {"supervised", "balanced", "higher_autonomy"}


def validate_dataset(df: pd.DataFrame, target_col: str = "target_autonomy") -> Dict[str, Any]:
    """Strict dataset validation before training; raises ValueError on schema or domain violations."""
    errors: List[str] = []
    warnings: List[str] = []

    expected_cols = set(REQUIRED_FEATURES) | {target_col}
    missing_cols = expected_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset missing required columns: {sorted(missing_cols)}")

    if len(df) < 100:
        raise ValueError(f"Insufficient dataset size ({len(df)} rows); minimum 100 rows required.")

    if df[target_col].isna().any():
        errors.append("Target column contains null values.")

    observed_classes = set(df[target_col].dropna().unique().tolist())
    invalid_classes = observed_classes - VALID_CLASSES
    if invalid_classes:
        errors.append(f"Unexpected target classes: {sorted(invalid_classes)}")
    if observed_classes != VALID_CLASSES:
        errors.append(f"Missing target classes: {sorted(VALID_CLASSES - observed_classes)}")

    # Domain range checks on non-null values
    bounds = {
        "prev_approvals": (0, 10000),
        "prev_rejections": (0, 10000),
        "user_corrections": (0, 10000),
        "interruptions_count": (0, 10000),
        "manual_step_edits": (0, 10000),
        "task_complexity": (0.0, 1.0),
        "task_risk_level": (0, 2),
        "prev_completion_rate": (0.0, 1.0),
        "intervention_frequency": (0.0, 100.0),
        "historical_recovery_rate": (0.0, 1.0),
    }
    missing_rates: Dict[str, float] = {}
    for col, (lo, hi) in bounds.items():
        series = pd.to_numeric(df[col], errors="coerce")
        miss_pct = float(series.isna().mean())
        missing_rates[col] = round(miss_pct, 4)
        if miss_pct > 0.25:
            errors.append(f"Feature '{col}' exceeds 25% missing values ({miss_pct:.1%}).")
        valid = series.dropna()
        if ((valid < lo) | (valid > hi)).any():
            errors.append(f"Feature '{col}' has values outside [{lo}, {hi}].")

    class_counts = df[target_col].value_counts().to_dict()
    min_class_ratio = min(class_counts.values()) / len(df)
    if min_class_ratio < 0.08:
        warnings.append(f"Severe class imbalance detected (min class ratio={min_class_ratio:.2%}).")

    if errors:
        raise ValueError("Dataset validation failed: " + "; ".join(errors))

    return {
        "valid": True,
        "row_count": int(len(df)),
        "class_distribution": {str(k): int(v) for k, v in class_counts.items()},
        "missing_rates": missing_rates,
        "warnings": warnings,
    }


def verify_disjoint_splits(train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray) -> None:
    s_train, s_val, s_test = set(train_idx.tolist()), set(val_idx.tolist()), set(test_idx.tolist())
    if (s_train & s_val) or (s_train & s_test) or (s_val & s_test):
        raise ValueError("Data leakage detected: train/validation/test index sets overlap!")
