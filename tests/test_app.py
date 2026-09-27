from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import users
from estimator.features import FEATURE_NAMES
from estimator.lookups import fill
from estimator.methods import ESTIMATORS

SAMPLE = Path("data/sample_property.csv").read_bytes()
SOLD = Path("data/the_sold_properties_V2.csv").read_bytes()


def run_app(username: str | None = None) -> AppTest:
    at = AppTest.from_file("../app.py", default_timeout=60)
    if username:
        at.session_state["username"] = username
    return at.run()


@pytest.fixture
def app():
    return run_app(username="ada")


@pytest.fixture
def logged_out(conn):
    return run_app()


def submit(at: AppTest, form: str, **fields: str) -> AppTest:
    for name, value in fields.items():
        at.text_input(key=f"{form}_{name}").input(value)
    return next(b for b in at.button if b.proto.form_id == form).click().run()


def upload(at, content, name="property.csv"):
    at.sidebar.file_uploader[0].set_value((name, content, "text/csv"))
    at.run()


def load(at):
    at.sidebar.button[0].click()
    at.run()


def estimate(at):
    at.button(key="FormSubmitter:features-Estimate price").click()
    at.run()


def test_logged_out_shows_only_the_log_in_form(logged_out):
    assert not logged_out.exception
    assert logged_out.title[0].value == "House price estimator"
    assert [tab.label for tab in logged_out.tabs] == ["Log in", "Sign up"]
    assert not logged_out.selectbox


def test_sign_up_logs_you_in(logged_out, conn):
    at = submit(logged_out, "sign_up", username="Ada", password="correct horse", confirm="correct horse")

    assert not at.exception
    assert at.session_state["username"] == "ada"
    assert at.selectbox(key="f_SUBURB").value == "-"
    assert users.authenticate(conn, "ada", "correct horse") == "ada"


def test_sign_up_passwords_must_match(logged_out):
    at = submit(logged_out, "sign_up", username="ada", password="correct horse", confirm="correct")

    assert at.error[0].value == "The passwords don't match."
    assert "username" not in at.session_state


def test_sign_up_shows_why_it_failed(logged_out, conn):
    users.sign_up(conn, "ada", "correct horse")

    at = submit(logged_out, "sign_up", username="ada", password="another one", confirm="another one")

    assert at.error[0].value == "The username ada is already taken."


def test_log_in(logged_out, conn):
    users.sign_up(conn, "ada", "correct horse")

    at = submit(logged_out, "log_in", username="ada", password="correct horse")

    assert at.session_state["username"] == "ada"
    assert "Signed in as **ada**" in [md.value for md in at.sidebar.markdown]


def test_log_in_with_the_wrong_password(logged_out, conn):
    users.sign_up(conn, "ada", "correct horse")

    at = submit(logged_out, "log_in", username="ada", password="battery staple")

    assert at.error[0].value == "Invalid username or password."
    assert "username" not in at.session_state


def test_log_out(app):
    app.sidebar.button(key="log_out").click().run()

    assert "username" not in app.session_state
    assert [tab.label for tab in app.tabs] == ["Log in", "Sign up"]


def test_app_renders_the_form(app):
    assert not app.exception
    assert app.title[0].value == "House price estimator"
    assert f"{len(ESTIMATORS)} independent estimates" in app.caption[0].value
    assert app.selectbox(key="f_SUBURB").value == "-"
    assert app.selectbox(key="f_PROPERTY_TYPE").value == "-"


def test_choosing_suburb_and_type_autofills_market_fields(app):
    app.selectbox(key="f_SUBURB").set_value("Mosman")
    app.selectbox(key="f_PROPERTY_TYPE").set_value("House")
    app.run()

    expected = fill("Mosman", "House")
    assert app.text_input(key="f_SUBURB_MEAN_PRICE").value == str(expected["SUBURB_MEAN_PRICE"])
    assert app.text_input(key="f_AVG_RENTAL_PRICE").value == str(expected["AVG_RENTAL_PRICE"])


def test_changing_property_type_refreshes_autofilled_fields(app):
    app.selectbox(key="f_SUBURB").set_value("Mosman")
    app.selectbox(key="f_PROPERTY_TYPE").set_value("House")
    app.run()
    app.selectbox(key="f_PROPERTY_TYPE").set_value("Apartment")
    app.run()

    expected = fill("Mosman", "Apartment")
    assert app.text_input(key="f_SUBURB_MEAN_PRICE").value == str(expected["SUBURB_MEAN_PRICE"])


def test_loading_a_single_row_csv_fills_the_form(app):
    upload(app, SAMPLE)
    load(app)

    assert not app.exception
    assert app.sidebar.success[0].value == f"Loaded {len(FEATURE_NAMES)} of {len(FEATURE_NAMES)} features."
    assert app.selectbox(key="f_SUBURB").value == "Mosman"
    assert app.selectbox(key="f_PROPERTY_TYPE").value == "Unit"
    assert app.selectbox(key="f_GARAGE_AREA").value == "0"
    assert app.selectbox(key="f_AIRCONDITIONER").value == "Yes"
    assert app.selectbox(key="f_SOLAR_PANEL").value == "No"
    assert app.checkbox(key="f_NEAR_GOOD_SCHOOLS").value is True
    assert app.multiselect(key="f_OUTDOOR_FEATURE").value == ["balcony", "garden"]
    assert app.text_input(key="f_LAND_SIZE").value == "1407.0"


def test_multi_row_csv_lets_the_user_pick_a_row(app):
    upload(app, SOLD)
    picker = app.sidebar.selectbox[0]
    assert picker.label.startswith("Property (")

    picker.set_value(1)
    app.run()
    load(app)

    assert not app.exception
    assert "3/17 MILNER ST" in app.sidebar.success[0].value
    assert app.selectbox(key="f_PROPERTY_CONDITION").value == "Renovated"
    assert app.multiselect(key="f_OUTDOOR_FEATURE").value == ["garden"]


def test_estimate_shows_one_metric_per_method_and_actual_price(app):
    upload(app, SAMPLE)
    load(app)
    estimate(app)

    assert not app.exception
    assert not app.error
    labels = [metric.label for metric in app.metric]
    for method in ESTIMATORS:
        assert method.label in labels
    assert "Actual sale price (from CSV)" in labels
    assert "Mean estimate" in labels
    actual = next(metric for metric in app.metric if metric.label == "Actual sale price (from CSV)")
    assert actual.value == "$1,450,000"
