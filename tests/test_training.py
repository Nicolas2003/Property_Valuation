from __future__ import annotations

import numpy as np
import pytest

from estimator.ml.dataset import training_frame
from estimator.ml.training import RISK_FEATURES, RISK_LEVELS, TRAINERS, MultiHotEncoder, build_preprocessor, fitted_models


@pytest.fixture(scope="module")
def training_data():
    return training_frame()


def test_multi_hot_encoder_splits_and_encodes_tokens():
    values = np.array([["balcony;garden"], ["pool"], ["garden"]], dtype=object)

    encoder = MultiHotEncoder().fit(values)

    assert list(encoder.encoder_.classes_) == ["balcony", "garden", "pool"]
    assert encoder.transform(values).tolist() == [[1, 1, 0], [0, 0, 1], [0, 1, 0]]


def test_multi_hot_encoder_supports_a_custom_separator():
    values = np.array([["balcony|deck"], ["deck"]], dtype=object)

    encoder = MultiHotEncoder(seperator="|").fit(values)

    assert encoder.transform(values).tolist() == [[1, 1], [0, 1]]


def test_multi_hot_encoder_names_its_output_columns():
    encoder = MultiHotEncoder().fit(np.array([["pool;deck"]], dtype=object))

    assert list(encoder.get_feature_names_out(["OUTDOOR_FEATURE"])) == ["OUTDOOR_FEATURE_deck", "OUTDOOR_FEATURE_pool"]
    assert list(encoder.get_feature_names_out()) == ["MULTI_deck", "MULTI_pool"]


def test_preprocessor_routes_columns_to_their_transformers(training_data):
    inputs, _ = training_data

    preprocessor = build_preprocessor(inputs)
    columns = {name: list(cols) for name, _, cols in preprocessor.transformers}

    assert "LAND_SIZE" in columns["numerical"]
    assert "SUBURB" in columns["categorical"]
    assert "OUTDOOR_FEATURE" not in columns["categorical"]
    assert "SALE_DATE" not in columns["categorical"]
    assert columns["multi_categorical"] == ["OUTDOOR_FEATURE"]
    assert columns["risk"] == RISK_FEATURES


def test_preprocessor_transforms_the_training_frame(training_data):
    inputs, _ = training_data

    preprocessor = build_preprocessor(inputs).fit(inputs)
    transformed = preprocessor.transform(inputs)
    names = list(preprocessor.get_feature_names_out())

    assert transformed.shape == (len(inputs), len(names))
    assert not np.isnan(transformed).any()
    assert "multi_categorical__OUTDOOR_FEATURE_garden" in names
    assert "categorical__SUBURB_Mosman" in names


def test_preprocessor_orders_risk_levels(training_data):
    inputs, _ = training_data

    preprocessor = build_preprocessor(inputs).fit(inputs)
    risk = preprocessor.named_transformers_["risk"].named_steps["encoder"]

    assert [list(levels) for levels in risk.categories_] == [RISK_LEVELS] * len(RISK_FEATURES)


@pytest.mark.parametrize("name", list(TRAINERS))
def test_trainer_fits_a_model_that_predicts_prices(name, training_data):
    inputs, outputs = training_data

    model = TRAINERS[name](inputs, outputs)
    predictions = model.predict(inputs)

    assert predictions.shape == (len(inputs),)
    assert model.score(inputs, outputs) > 0.5
    assert 100_000 < float(np.median(predictions)) < 20_000_000


def test_gradient_boost_imputes_numbers_with_the_mean(training_data):
    inputs, outputs = training_data

    model = TRAINERS["gradient_boosting"](inputs, outputs)
    imputer = model.named_steps["preprocessor"].named_transformers_["numerical"].named_steps["imputer"]

    assert imputer.strategy == "mean"


def test_fitted_models_trains_every_method_once():
    models = fitted_models()

    assert set(models) == set(TRAINERS)
    assert fitted_models() is models
