from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ..contract import Features
from ..features import FEATURE_NAMES
from .dataset import GROWTH_FEATURES, _finite, _split, growth_features, sale_history
from .training import MultiHotEncoder

SAVED_MODELS = Path(__file__).resolve().parent / "saved_models"

PRICE_FEATURES = ["MEAN_PRICE", *GROWTH_FEATURES]

UNCOLLECTED = {"RECENT_SALE_RATE_PERCENT": np.nan}

OUTDOOR_UNSTATED = "unstated"

UNUSED_BY_MODEL = ("SALE_DATE", "PREV_SALE_PRICE")


@lru_cache(maxsize=1)
def saved_models() -> dict[str, Any]:
    sys.modules["__main__"].MultiHotEncoder = MultiHotEncoder
    models = {}
    for path in sorted(SAVED_MODELS.glob("*.pkl")):
        models[path.stem] = joblib.load(path)
    return models


def history_features(prev_dates: Any, prev_prices: Any) -> dict[str, float]:
    out = dict.fromkeys(PRICE_FEATURES, np.nan)

    history = sale_history(prev_dates, prev_prices)
    if history is None:
        return out
    dates, prices = history

    out["MEAN_PRICE"] = prices.mean()
    out.update(growth_features(dates, prices))
    return _finite(out)


def _numeric_columns(model: Any) -> list[str]:
    pipeline = getattr(model, "regressor_", model)
    preprocessor = pipeline.named_steps["preprocessor"]
    for name, _, columns in preprocessor.transformers_:
        if name == "numerical":
            return list(columns)
    return []


def to_saved_frame(features: Features, model: Any) -> pd.DataFrame:
    row: dict[str, Any] = {}
    for name in FEATURE_NAMES:
        value = features.get(name)
        row[name] = np.nan if value is None else value
    if features.get("OUTDOOR_FEATURE") is None:
        row["OUTDOOR_FEATURE"] = OUTDOOR_UNSTATED
    row.update(UNCOLLECTED)
    row.update(history_features(features.get("PREV_SALE_DATE"), features.get("PREV_SALE_PRICE")))

    columns = list(model.feature_names_in_)
    frame = pd.DataFrame([row])[columns].astype(object)
    numeric = _numeric_columns(model)
    frame[numeric] = frame[numeric].astype("float64")
    return frame


def model_inputs(model: Any) -> list[str]:
    inputs = []
    for name in model.feature_names_in_:
        if name in FEATURE_NAMES and name not in UNUSED_BY_MODEL:
            inputs.append(name)
    return inputs


def blank_inputs(features: Features, model: Any) -> tuple[int, int]:
    inputs = model_inputs(model)
    blank = 0
    for name in inputs:
        if name == "PREV_SALE_DATE":
            blank += not _split(features.get(name))
        elif features.get(name) is None:
            blank += 1
    return blank, len(inputs)


__all__ = [
    "OUTDOOR_UNSTATED",
    "PRICE_FEATURES",
    "SAVED_MODELS",
    "blank_inputs",
    "history_features",
    "model_inputs",
    "saved_models",
    "to_saved_frame",
]
