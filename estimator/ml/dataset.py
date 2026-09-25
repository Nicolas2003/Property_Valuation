from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..contract import Features
from ..features import FEATURE_NAMES

DATASET = Path(__file__).resolve().parents[2] / "data" / "the_sold_properties_V2.csv"

EXCLUDED = ("SALE_PRICE", "ADDRESS")

HISTORY_COLUMNS = ("PREV_SALE_DATE", "PREV_SALE_PRICE")


def _model_inputs() -> list[str]:
    excluded = EXCLUDED + HISTORY_COLUMNS
    names: list[str] = []
    for name in FEATURE_NAMES:
        if name not in excluded:
            names.append(name)
    return names


MODEL_INPUTS: list[str] = _model_inputs()

HISTORY_FEATURES = [
    "PRICE_GROWTH",
    "PRICE_RATE",
    "MEAN_PRICE",
    "MEAN_PRICE_RATE",
    "MEAN_SALE_PERCENTAGE",
    "MEAN_SALE_RATE_PERCENTAGE",
    "LAST_SALE_PRICE",
    "YEARS_SINCE_LAST_SALE",
]

GROWTH_FEATURES = [
    "PRICE_GROWTH",
    "PRICE_RATE",
    "MEAN_PRICE_RATE",
    "MEAN_SALE_PERCENTAGE",
    "MEAN_SALE_RATE_PERCENTAGE",
]

COLUMNS: list[str] = MODEL_INPUTS + HISTORY_FEATURES

TARGET = "SALE_PRICE"


def _split(raw: Any) -> list[str]:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return []
    text = str(raw).strip()
    if not text:
        return []
    items = []
    for item in text.split(";"):
        item = item.strip()
        if item:
            items.append(item)
    return items


def sale_history(prev_dates: Any, prev_prices: Any) -> tuple[pd.DatetimeIndex, np.ndarray] | None:
    dates_raw, prices_raw = _split(prev_dates), _split(prev_prices)
    if not dates_raw or len(dates_raw) != len(prices_raw):
        return None

    try:
        dates = pd.to_datetime(dates_raw)
        prices_list = []
        for price in prices_raw:
            prices_list.append(float(price))
        prices = np.array(prices_list)
    except (ValueError, TypeError):
        return None

    order = np.argsort(dates)
    return dates[order], prices[order]


def growth_features(dates: pd.DatetimeIndex, prices: np.ndarray) -> dict[str, float]:
    if len(prices) < 2:
        return dict.fromkeys(GROWTH_FEATURES, np.nan)

    time_diffs = np.diff(dates).astype("timedelta64[D]").astype(float) / 365.25
    price_diffs = np.diff(prices)

    out = {"PRICE_GROWTH": prices[-1] - prices[0]}
    with np.errstate(divide="ignore", invalid="ignore"):
        out["PRICE_RATE"] = out["PRICE_GROWTH"] / time_diffs.sum()
        out["MEAN_PRICE_RATE"] = (price_diffs / time_diffs).mean()

        sale_percentages = (price_diffs / prices[:-1]) * 100
        out["MEAN_SALE_PERCENTAGE"] = sale_percentages.mean()
        out["MEAN_SALE_RATE_PERCENTAGE"] = (sale_percentages / time_diffs).mean()
    return out


def computed_features(prev_dates: Any, prev_prices: Any, sale_date: Any = None) -> dict[str, float]:
    out = dict.fromkeys(HISTORY_FEATURES, np.nan)

    history = sale_history(prev_dates, prev_prices)
    if history is None:
        return out
    dates, prices = history

    out["LAST_SALE_PRICE"] = prices[-1]

    anchor = _as_timestamp(sale_date) or pd.Timestamp.today().normalize()
    out["YEARS_SINCE_LAST_SALE"] = (anchor - dates[-1]).days / 365.25

    if len(prices) < 2:
        return _finite(out)

    out["MEAN_PRICE"] = prices.mean()
    out.update(growth_features(dates, prices))
    return _finite(out)


def _finite(computed: dict[str, float]) -> dict[str, float]:
    finite = {}
    for name, value in computed.items():
        if np.isfinite(value):
            finite[name] = value
        else:
            finite[name] = np.nan
    return finite


def _as_timestamp(value: Any) -> pd.Timestamp | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return pd.Timestamp(value)
    try:
        return pd.Timestamp(str(value))
    except ValueError:
        return None


def load() -> pd.DataFrame:
    return pd.read_csv(DATASET)


def _history_row(row: pd.Series) -> pd.Series:
    return pd.Series(
        computed_features(
            row["PREV_SALE_DATE"], row["PREV_SALE_PRICE"], row.get("SALE_DATE")
        )
    )


@lru_cache(maxsize=1)
def training_frame() -> tuple[pd.DataFrame, pd.Series]:
    df = load()
    history = df.apply(_history_row, axis=1)
    frame = pd.concat([df, history], axis=1)[COLUMNS]

    numeric = frame.select_dtypes(include=["number"]).columns
    frame[numeric] = frame[numeric].astype("float64")
    return frame, df[TARGET]


@lru_cache(maxsize=1)
def _dtypes() -> pd.Series:
    return training_frame()[0].dtypes


def to_frame(features: Features) -> pd.DataFrame:
    row: dict[str, Any] = {}
    for name in MODEL_INPUTS:
        value = features.get(name)
        row[name] = np.nan if value is None else value
    row.update(
        computed_features(
            features.get("PREV_SALE_DATE"),
            features.get("PREV_SALE_PRICE"),
            features.get("SALE_DATE"),
        )
    )
    return pd.DataFrame([row], columns=COLUMNS).astype(_dtypes())


def blank_count(features: Features) -> int:
    unanswered = 0
    for name in MODEL_INPUTS:
        if features.get(name) is None:
            unanswered += 1
    if not _split(features.get("PREV_SALE_DATE")):
        unanswered += 1
    return unanswered


INPUT_COUNT = len(MODEL_INPUTS) + 1

__all__ = [
    "COLUMNS",
    "DATASET",
    "GROWTH_FEATURES",
    "HISTORY_FEATURES",
    "INPUT_COUNT",
    "MODEL_INPUTS",
    "blank_count",
    "computed_features",
    "growth_features",
    "load",
    "sale_history",
    "to_frame",
    "training_frame",
]
