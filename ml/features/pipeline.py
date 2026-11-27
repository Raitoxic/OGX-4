from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RAW_FEATURES: List[str] = [
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

ENGINEERED_FEATURE_NAMES: List[str] = RAW_FEATURES + [
    "rejection_ratio",
    "correction_intensity",
    "risk_x_complexity",
    "reliability_deficit",
    "stability_index",
]


class SupervisionFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Deterministic domain feature engineering operating on imputed numeric arrays
    strictly inside the sklearn Pipeline to prevent train/val/test leakage.
    """

    def fit(self, X: np.ndarray, y=None):
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        arr = np.asarray(X, dtype=np.float64)
        approvals = arr[:, 0]
        rejections = arr[:, 1]
        corrections = arr[:, 2]
        interrupts = arr[:, 3]
        edits = arr[:, 4]
        complexity = arr[:, 5]
        risk = arr[:, 6]
        completion_rate = arr[:, 7]
        interventions = arr[:, 8]
        recovery_rate = arr[:, 9]

        rejection_ratio = rejections / (approvals + rejections + 1.0)
        correction_intensity = (corrections + edits + interrupts) / (approvals + 1.0)
        risk_x_complexity = (risk / 2.0) * complexity
        reliability_deficit = (1.0 - completion_rate) + (1.0 - recovery_rate)
        stability_index = np.log1p(approvals) * completion_rate / (1.0 + interventions + rejections)

        extra = np.column_stack(
            [
                rejection_ratio,
                correction_intensity,
                risk_x_complexity,
                reliability_deficit,
                stability_index,
            ]
        )
        return np.hstack([arr, extra])


def build_feature_preprocessor(scale: bool = True) -> Pipeline:
    steps = [
        ("imputer", SimpleImputer(strategy="median")),
        ("engineer", SupervisionFeatureEngineer()),
    ]
    if scale:
        steps.append(("scaler", StandardScaler()))
    return Pipeline(steps)


def rule_based_baseline_predict(df: pd.DataFrame) -> np.ndarray:
    """
    Simple interpretable rule-based baseline comparator.
    Predicts 'supervised', 'balanced', or 'higher_autonomy' using transparent fixed thresholds.
    """
    preds: List[str] = []
    for _, row in df.iterrows():
        risk = float(row["task_risk_level"]) if pd.notna(row["task_risk_level"]) else 1.0
        rejections = float(row["prev_rejections"]) if pd.notna(row["prev_rejections"]) else 0.0
        interrupts = float(row["interruptions_count"]) if pd.notna(row["interruptions_count"]) else 0.0
        completion = float(row["prev_completion_rate"]) if pd.notna(row["prev_completion_rate"]) else 0.8
        approvals = float(row["prev_approvals"]) if pd.notna(row["prev_approvals"]) else 0.0
        complexity = float(row["task_complexity"]) if pd.notna(row["task_complexity"]) else 0.5

        if risk >= 2.0 or rejections >= 3.0 or interrupts >= 3.0 or completion < 0.60:
            preds.append("supervised")
        elif risk <= 0.0 and rejections == 0.0 and interrupts <= 1.0 and approvals >= 6.0 and complexity <= 0.55:
            preds.append("higher_autonomy")
        else:
            preds.append("balanced")
    return np.array(preds)
