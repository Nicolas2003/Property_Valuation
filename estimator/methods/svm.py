from __future__ import annotations

from ..contract import Estimate, Features
from ._model import estimate_with

LABEL = "Support Vector Machine"
BLURB = "A polynomial-kernel regressor fitted on Sydney sales."


def estimate(features: Features) -> Estimate:
    return estimate_with("svm", features)
