from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import label_binarize

CLASSES: List[str] = ["supervised", "balanced", "higher_autonomy"]


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    model_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    acc = float(accuracy_score(y_true, y_pred))
    prec_macro = float(precision_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0))
    f1_macro = float(f1_score(y_true, y_pred, labels=CLASSES, average="macro", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=CLASSES).tolist()
    report_raw = classification_report(
        y_true, y_pred, labels=CLASSES, output_dict=True, zero_division=0
    )
    class_report = {
        cls: {
            "precision": round(float(report_raw[cls]["precision"]), 4),
            "recall": round(float(report_raw[cls]["recall"]), 4),
            "f1_score": round(float(report_raw[cls]["f1-score"]), 4),
            "support": int(report_raw[cls]["support"]),
        }
        for cls in CLASSES
    }

    roc_auc: Optional[float] = None
    if y_proba is not None and model_classes is not None:
        try:
            # Align probability columns to canonical CLASSES ordering
            col_order = [list(model_classes).index(c) for c in CLASSES]
            aligned_proba = y_proba[:, col_order]
            y_bin = label_binarize(y_true, classes=CLASSES)
            roc_auc = round(float(roc_auc_score(y_bin, aligned_proba, average="macro", multi_class="ovr")), 4)
        except Exception:
            roc_auc = None

    return {
        "accuracy": round(acc, 4),
        "precision_macro": round(prec_macro, 4),
        "recall_macro": round(rec_macro, 4),
        "f1_macro": round(f1_macro, 4),
        "roc_auc_ovr": roc_auc,
        "classes": CLASSES,
        "confusion_matrix": cm,
        "class_report": class_report,
    }


def benchmark_inference_latency(model, X_sample: pd.DataFrame, n_runs: int = 150) -> Dict[str, float]:
    """Measures single-row inference latency (ms) to mirror live production API calls."""
    single_row = X_sample.iloc[[0]]
    # Warm-up
    model.predict_proba(single_row)

    latencies_ms: List[float] = []
    for i in range(n_runs):
        row = X_sample.iloc[[i % len(X_sample)]]
        t0 = time.perf_counter()
        model.predict_proba(row)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    arr = np.array(latencies_ms)
    return {
        "mean_ms": round(float(np.mean(arr)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "runs": n_runs,
    }
