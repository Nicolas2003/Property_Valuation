from __future__ import annotations

from ..contract import Method
from . import decision_tree, random_forest, svm, xgb

ESTIMATORS: list[Method] = [
    Method("random_forest", random_forest.LABEL, random_forest.BLURB, random_forest.estimate),
    Method("svm", svm.LABEL, svm.BLURB, svm.estimate),
    Method("xgboost", xgb.LABEL, xgb.BLURB, xgb.estimate),
    Method("decision_tree", decision_tree.LABEL, decision_tree.BLURB, decision_tree.estimate),
]

__all__ = ["ESTIMATORS"]
