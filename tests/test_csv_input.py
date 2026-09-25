from __future__ import annotations

import pytest

from estimator.csv_input import list_rows, read_csv, row_label

SOLD = "data/the_sold_properties_V2.csv"

TWO_ROWS = """SUBURB,LAND_SIZE,ADDRESS,SALE_PRICE
Mosman,1407,"13/5 THE ESPLANADE, MOSMAN, NSW 2088",1450000
Mosman,717,,790000
"""


def test_read_csv_loads_the_chosen_row():
    upload = read_csv(TWO_ROWS, row=1)

    assert upload.ok, [str(e) for e in upload.report.errors]
    assert upload.features["LAND_SIZE"] == pytest.approx(717.0)
    assert upload.actual_price == pytest.approx(790000.0)


def test_read_csv_defaults_to_the_first_row():
    upload = read_csv(TWO_ROWS)

    assert upload.features["LAND_SIZE"] == pytest.approx(1407.0)


@pytest.mark.parametrize("row", [-1, 2])
def test_read_csv_rejects_a_row_outside_the_file(row):
    upload = read_csv(TWO_ROWS, row=row)

    assert not upload.ok
    assert f"row index {row}" in str(upload.report.errors[0])
    assert "#1–#2" in str(upload.report.errors[0])


def test_empty_file_is_an_error():
    rows, report = list_rows("SUBURB,LAND_SIZE\n")

    assert rows == []
    assert not report.ok


def test_row_label_uses_the_address_when_present():
    rows, _ = list_rows(TWO_ROWS)

    assert row_label(0, rows[0]) == "#1 — 13/5 THE ESPLANADE, MOSMAN, NSW 2088"
    assert row_label(1, rows[1]) == "#2"


def test_every_sold_property_loads():
    with open(SOLD, "rb") as fh:
        rows, report = list_rows(fh)

    assert report.ok
    assert len(rows) == 150
    for index in range(len(rows)):
        with open(SOLD, "rb") as fh:
            upload = read_csv(fh, row=index)
        assert upload.ok, (index, [str(e) for e in upload.report.errors])
        assert upload.actual_price
