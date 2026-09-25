from __future__ import annotations

from ..contract import Estimate, Features
from ._model import estimate_with

LABEL = "Random Forest"
BLURB = "500 decision trees fitted on Sydney sales, their predictions averaged."


def estimate(features: Features) -> Estimate:
    return estimate_with("random_forest", features)
