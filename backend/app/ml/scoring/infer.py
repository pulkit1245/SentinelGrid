"""
Inference wrapper for the Compound-Risk XGBoost Scorer.

Loads model.pkl once at worker startup and exposes score(features) -> 0-100,
called by the Compound Risk Agent (see compound_risk_agent.py's `scorer`
constructor arg -- pass `infer.score` directly).
"""

import pickle
from pathlib import Path
from typing import Optional

from .train import FEATURE_COLUMNS, MODEL_PATH


class CompoundRiskScorer:
    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"No trained model at {self.model_path}. Run "
                "`python -m backend.app.ml.scoring.train` first."
            )
        with open(self.model_path, "rb") as f:
            bundle = pickle.load(f)
        self.model = bundle["model"]
        self.feature_columns = bundle["feature_columns"]

    def score(self, features: dict) -> float:
        """
        `features` should contain (at least) the keys in FEATURE_COLUMNS;
        missing keys default to 0.0 so this degrades gracefully if a caller
        hasn't wired up every feature yet (e.g. before Module 3's RAG
        historical-incident-similarity signal exists).

        Returns a 0-100 risk score (P(compound_risk) * 100).
        """
        row = [[features.get(col, 0.0) for col in self.feature_columns]]
        prob = self.model.predict_proba(row)[0][1]
        return round(float(prob) * 100, 2)


_singleton: Optional[CompoundRiskScorer] = None


def get_scorer() -> CompoundRiskScorer:
    """Process-wide singleton so the model is only loaded once."""
    global _singleton
    if _singleton is None:
        _singleton = CompoundRiskScorer()
    return _singleton


def score(features: dict) -> float:
    """Module-level convenience matching the `scorer(features) -> float` signature CompoundRiskAgent expects."""
    return get_scorer().score(features)
