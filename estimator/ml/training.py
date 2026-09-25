from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    MultiLabelBinarizer,
    OneHotEncoder,
    OrdinalEncoder,
    StandardScaler,
)
from sklearn.svm import SVR

from .dataset import training_frame

MULTI_FEATURE = "OUTDOOR_FEATURE"

RISK_FEATURES = ["FLOOD_RISK", "BUSHFIRE_RISK", "COASTAL_EROSION_RISK"]
RISK_LEVELS = ["Nil", "Low", "Medium", "High"]

EXCLUDE_CATEGORICAL = [MULTI_FEATURE, "SALE_DATE", *RISK_FEATURES]


class MultiHotEncoder(BaseEstimator, TransformerMixin):
    def __init__(self, seperator: str = ";"):
        self.seperator = seperator

    def _split_values(self, X, known=None):
        split_values = []
        for value in X[:, 0]:
            tokens = []
            for item in value.split(self.seperator):
                if known is not None and item not in known:
                    continue
                tokens.append(item.strip())
            split_values.append(tokens)
        return split_values

    def fit(self, X, y=None):
        self.encoder_ = MultiLabelBinarizer()
        self.encoder_.fit(self._split_values(X))
        return self

    def transform(self, X):
        known = set(self.encoder_.classes_)
        return self.encoder_.transform(self._split_values(X, known))

    def get_feature_names_out(self, input_features=None):
        feature = input_features[0] if input_features is not None else "MULTI"
        names = []
        for category in self.encoder_.classes_:
            names.append(f"{feature}_{category}")
        return np.array(names)


def build_preprocessor(frame: pd.DataFrame) -> ColumnTransformer:
    numerical_features = frame.select_dtypes(include=["int64", "float64"]).columns
    categorical_features = frame.select_dtypes(
        include=["string", "category", "object"]
    ).columns.drop(EXCLUDE_CATEGORICAL, errors="ignore")

    numerical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    multi_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", MultiHotEncoder(seperator=";")),
    ])

    risk_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(categories=[RISK_LEVELS] * len(RISK_FEATURES))),
    ])

    return ColumnTransformer([
        ("numerical", numerical_transformer, numerical_features),
        ("categorical", categorical_transformer, categorical_features),
        ("multi_categorical", multi_transformer, [MULTI_FEATURE]),
        ("risk", risk_transformer, RISK_FEATURES),
    ])


def train_random_forest(train_inputs, train_outputs):
    model = Pipeline([
        ("preprocessor", build_preprocessor(train_inputs)),
        ("regressor", RandomForestRegressor(
            n_estimators=500, max_depth=3, max_features=0.5,
            min_samples_leaf=2, min_samples_split=2, random_state=42,
        )),
    ])
    model.fit(train_inputs, train_outputs)
    return model


def train_svm(train_inputs, train_outputs):
    pipeline = Pipeline([
        ("preprocessor", build_preprocessor(train_inputs)),
        ("scaler", StandardScaler()),
        ("regressor", SVR(kernel="poly", C=1, degree=2, epsilon=0.1, gamma="scale")),
    ])
    model = TransformedTargetRegressor(regressor=pipeline, transformer=StandardScaler())
    model.fit(train_inputs, train_outputs)
    return model


def train_gradient_boost(train_inputs, train_outputs):
    preprocessor = build_preprocessor(train_inputs)
    preprocessor.set_params(
        numerical__imputer__strategy="mean"
    )
    model = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", GradientBoostingRegressor(
            learning_rate=0.3, max_depth=7, min_samples_leaf=2,
            min_samples_split=10, n_estimators=400, random_state=42,
        )),
    ])
    model.fit(train_inputs, train_outputs)
    return model


TRAINERS = {
    "random_forest": train_random_forest,
    "svm": train_svm,
    "gradient_boosting": train_gradient_boost,
}


@lru_cache(maxsize=1)
def fitted_models() -> dict[str, object]:
    inputs, outputs = training_frame()
    models = {}
    for name, train in TRAINERS.items():
        models[name] = train(inputs, outputs)
    return models


__all__ = ["MultiHotEncoder", "build_preprocessor", "fitted_models", "TRAINERS"]
