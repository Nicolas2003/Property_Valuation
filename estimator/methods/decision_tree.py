from __future__ import annotations

from ..contract import Estimate, Features
from ._model import estimate_with

LABEL = "Decision Tree"
BLURB = "A single regression tree, up to 10 levels deep, fitted on Sydney sales."


def estimate(features: Features) -> Estimate:
    return estimate_with("decision_tree", features)
