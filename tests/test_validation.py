from __future__ import annotations

import pytest

from estimator.features import BY_NAME
from estimator.validation import parse, validate


def test_unknown_category_lists_the_choices():
    value, issue = parse(BY_NAME["SUBURB"], "Atlantis")

    assert value is None
    assert "`Atlantis` is not one of:" in issue.message
    assert "Mosman" in issue.message


@pytest.mark.parametrize(
    ("name", "text", "what"),
    [
        ("PREV_SALE_DATE", "2020-01-01;01/02/2021", "a date in YYYY-MM-DD form"),
        ("PREV_SALE_PRICE", "520000;lots", "a finite number"),
    ],
)
def test_bad_list_entries_are_named(name, text, what):
    value, issue = parse(BY_NAME[name], text)

    assert value is None
    assert f"is not {what}" in issue.message


def test_renovation_before_build_year_is_a_warning():
    report = validate({"BUILT_YEAR": 2000, "RENOVATION_YEAR": 1990})

    assert any(w.name == "RENOVATION_YEAR" and "before the build year (2000)" in w.message for w in report.warnings)


def test_postcode_not_matching_the_suburb_is_a_warning():
    report = validate({"SUBURB": "Mosman", "POSTCODE": "2000"})

    assert any(w.name == "POSTCODE" and "not the postcode for Mosman (2088)" in w.message for w in report.warnings)


def test_matching_postcode_is_not_a_warning():
    report = validate({"SUBURB": "Mosman", "POSTCODE": "2088"})

    assert not any(w.name == "POSTCODE" for w in report.warnings)
