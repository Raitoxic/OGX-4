from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd

from ml.data.generate_dataset import ML_ROOT
from ml.features.pipeline import RAW_FEATURES

REGISTRY_PATH = ML_ROOT / "models" / "registry.json"
REPORT_PATH = ML_ROOT / "evaluation" / "latest_evaluation_report.json"


class SupervisionPredictor:
    """
    Production inference service for the VYRO-X Adaptive Supervision Prediction Model.
    Returns advisory autonomy recommendations ONLY — never overrides manual user settings,
    locked steps, or mandatory high-risk approval requirements.
    """

    def __init__(self) -> None:
        self._bundle: Optional[Dict[str, Any]] = None
        self._loaded_version: Optional[str] = None

    def reload(self) -> bool:
        if not REGISTRY_PATH.exists():
            self._bundle = None
            self._loaded_version = None
            return False
        try:
            reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            active_ver = reg.get("active_version")
            entry = next((v for v in reg.get("versions", []) if v["model_version"] == active_ver), None)
            if not entry:
                return False
            raw_path = entry["artifact_path"]
            project_root = ML_ROOT.parent
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = project_root / candidate
            if not candidate.exists():
                candidate = ML_ROOT / "models" / Path(raw_path).name
            if not candidate.exists():
                return False
            self._bundle = joblib.load(candidate)
            self._loaded_version = active_ver
            return True
        except Exception:
            self._bundle = None
            self._loaded_version = None
            return False

    def _ensure_loaded(self) -> bool:
        if self._bundle is not None:
            return True
        return self.reload()

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        if not REPORT_PATH.exists():
            return None
        try:
            return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predicts recommended autonomy mode with calibrated probabilities & inference latency."""
        if not self._ensure_loaded() or self._bundle is None:
            return {
                "available": False,
                "recommended_autonomy": "balanced",
                "probabilities": {"supervised": 0.33, "balanced": 0.34, "higher_autonomy": 0.33},
                "confidence": 0.0,
                "model_version": "untrained",
                "algorithm": "fallback",
                "dataset_provenance": "MODEL_NOT_TRAINED",
                "inference_latency_ms": 0.0,
                "explanation": "ML supervision model artifact not yet trained. Run ml/training/train.py.",
                "safety_notice": "Advisory only — manual autonomy settings and high-risk approval gates remain strictly enforced.",
            }

        row_dict = {}
        for col in RAW_FEATURES:
            val = features.get(col)
            row_dict[col] = float(val) if val is not None else float("nan")
        X_df = pd.DataFrame([row_dict], columns=RAW_FEATURES)

        model = self._bundle["model"]
        t0 = time.perf_counter()
        proba_arr = model.predict_proba(X_df)[0]
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        classes = list(model.classes_)
        probs = {str(c): round(float(p), 4) for c, p in zip(classes, proba_arr)}
        best_class = max(probs.keys(), key=lambda c: probs[c])
        confidence = probs[best_class]

        risk_label = {0: "low", 1: "medium", 2: "high"}.get(int(features.get("task_risk_level", 1)), "medium")
        explanation = (
            f"Recommended '{best_class.replace('_', ' ')}' (p={confidence:.2f}) given "
            f"{risk_label}-risk profile, complexity={float(features.get('task_complexity', 0.5)):.2f}, "
            f"{int(features.get('prev_rejections', 0))} rejection(s), and "
            f"{int(features.get('interruptions_count', 0))} interruption(s)."
        )

        return {
            "available": True,
            "recommended_autonomy": best_class,
            "probabilities": probs,
            "confidence": confidence,
            "model_version": self._bundle["model_version"],
            "algorithm": self._bundle["algorithm"],
            "dataset_provenance": self._bundle["dataset_provenance"],
            "inference_latency_ms": latency_ms,
            "explanation": explanation,
            "safety_notice": (
                "Advisory recommendation from synthetic demo model — never overrides manual user controls, "
                "locked steps, or mandatory high-risk approval gates."
            ),
        }


supervision_predictor = SupervisionPredictor()
