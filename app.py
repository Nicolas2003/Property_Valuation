from __future__ import annotations

from typing import Any

import streamlit as st

from estimator.csv_input import list_rows, read_row, row_label
from estimator.features import (
    BY_NAME,
    DERIVED_NAMES,
    FEATURE_NAMES,
    GARAGE_LABELS,
    OUTDOOR_NONE,
    SECTIONS,
    FeatureSpec,
    by_section,
)
from estimator.lookups import fill, known_suburbs
from estimator.methods import ESTIMATORS
from estimator.validation import parse_all

LEADING = ["SUBURB", "PROPERTY_TYPE"]

BLANK = "—"
TRISTATE = [BLANK, "Yes", "No"]

PLACEHOLDERS = {
    "date": "YYYY-MM-DD",
    "date_list": "2011-11-28;2006-06-24",
    "number_list": "520000;420500",
}

st.set_page_config(page_title="House price estimator", layout="wide")


def key(name: str) -> str:
    return f"f_{name}"


def get_raw(name: str) -> Any:
    return st.session_state.get(key(name))


def chosen(name: str) -> str | None:
    value = get_raw(name)
    return None if value in (None, "", BLANK) else value


def set_raw(name: str, value: Any) -> None:
    st.session_state[key(name)] = value


def apply_autofill() -> None:
    values = fill(chosen("SUBURB"), chosen("PROPERTY_TYPE"))
    previous = st.session_state.setdefault("_autofilled", {})
    for name in DERIVED_NAMES:
        if name not in values:
            continue
        current = get_raw(name)
        if current in (None, "", previous.get(name)):
            set_raw(name, str(values[name]))
    autofilled = {}
    for name, value in values.items():
        if name in DERIVED_NAMES:
            autofilled[name] = str(value)
    st.session_state["_autofilled"] = autofilled


def load_upload(upload) -> None:
    for name, value in upload.features.items():
        spec = BY_NAME[name]
        if value is None:
            set_raw(name, [] if spec.kind == "multiselect" else ("" if spec.kind != "binary" else False))
        elif spec.kind == "binary":
            set_raw(name, bool(value))
        elif spec.kind == "tristate":
            set_raw(name, "Yes" if value else "No")
        elif spec.kind == "multiselect":
            tokens = str(value).split(";")
            selected = []
            for token in tokens:
                if token != OUTDOOR_NONE:
                    selected.append(token)
            set_raw(name, selected)
            st.session_state[key(name) + "_none"] = tokens == [OUTDOOR_NONE]
        elif spec.kind == "category" and name == "GARAGE_AREA":
            set_raw(name, str(int(float(value))))
        else:
            set_raw(name, str(value))
    st.session_state["actual_price"] = upload.actual_price
    st.session_state["_autofilled"] = {}


def garage_label(value: str) -> str:
    return GARAGE_LABELS.get(value, value)


def plain_label(value: str) -> str:
    return value


def widget(spec: FeatureSpec) -> None:
    label = spec.label
    if spec.derived:
        label += " ·auto"
    args = {"key": key(spec.name), "help": spec.help_text or None}

    if spec.kind == "binary":
        st.markdown("<div style='height:1.85rem'></div>", unsafe_allow_html=True)
        st.checkbox(label, **args)
    elif spec.kind == "tristate":
        st.selectbox(label, TRISTATE, **args)
    elif spec.kind == "category":
        options = [BLANK] + spec.choices
        if spec.name == "GARAGE_AREA":
            fmt = garage_label
        else:
            fmt = plain_label
        st.selectbox(label, options, format_func=fmt, **args)
    elif spec.kind == "multiselect":
        st.multiselect(label, spec.choices, **args)
        st.checkbox(
            "…none of these (recorded, not unknown)",
            key=key(spec.name) + "_none",
            help="Tick when the property is known to have no outdoor feature.",
        )
    else:
        placeholder = PLACEHOLDERS.get(spec.kind, spec.unit)
        st.text_input(label, placeholder=placeholder, **args)


def collect() -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for name in FEATURE_NAMES:
        spec = BY_NAME[name]
        value = get_raw(name)
        if spec.kind == "binary":
            raw[name] = "1" if value else "0"
        elif spec.kind == "tristate":
            raw[name] = {"Yes": "1", "No": "0"}.get(value)
        elif spec.kind == "multiselect":
            if st.session_state.get(key(name) + "_none"):
                raw[name] = OUTDOOR_NONE
            else:
                raw[name] = ";".join(value or [])
        elif spec.kind == "category":
            raw[name] = None if value in (None, BLANK) else value
        else:
            raw[name] = value
    return raw


st.title("House price estimator")
st.caption(
    f"{len(FEATURE_NAMES)} property, location and market features: "
    f"{len(ESTIMATORS)} independent estimates."
)

with st.sidebar:
    st.subheader("Load a property")
    st.write(
        "A CSV with a header row and one or more data rows. Any subset of columns is fine; "
        "with several rows, pick the property to load."
    )
    uploaded = st.file_uploader("CSV file", type="csv", label_visibility="collapsed")
    rows = []
    selected = 0
    if uploaded is not None:
        if st.session_state.get("_rows_file") != uploaded.file_id:
            st.session_state["_rows"] = list_rows(uploaded.getvalue())
            st.session_state["_rows_file"] = uploaded.file_id
        rows, rows_report = st.session_state["_rows"]
        for error in rows_report.errors:
            st.error(str(error))
        if len(rows) > 1:
            selected = st.selectbox(
                f"Property ({len(rows)} rows)",
                range(len(rows)),
                format_func=lambda index: row_label(index, rows[index]),
            )
    if rows and st.button("Load into form", use_container_width=True):
        result = read_row(rows[selected])
        if result.ok:
            load_upload(result)
            loaded = f"row {row_label(selected, rows[selected])}: " if len(rows) > 1 else ""
            st.success(f"Loaded {loaded}{result.recognised} of {len(FEATURE_NAMES)} features.")
            if result.unknown_columns:
                st.info("Ignored unknown columns: " + ", ".join(result.unknown_columns))
            for warning in result.report.warnings:
                st.warning(str(warning))
        else:
            for error in result.report.errors:
                st.error(str(error))
    st.divider()
    st.caption("Samples: `data/sample_property.csv` (one row), `data/the_sold_properties_V2.csv` (150 rows)")

st.subheader("Where and what")
lead = st.columns(len(LEADING))
for column, name in zip(lead, LEADING):
    with column:
        widget(BY_NAME[name])
apply_autofill()

if chosen("SUBURB") and chosen("SUBURB") not in known_suburbs():
    st.info(
        f"No market data collected for {chosen('SUBURB')}. "
        "The auto-filled fields are left blank — enter them by hand if you have them."
    )

with st.form("features"):
    for section in SECTIONS:
        specs = []
        for spec in by_section(section):
            if spec.name not in LEADING:
                specs.append(spec)
        if not specs:
            continue
        derived_count = 0
        for spec in specs:
            if spec.derived:
                derived_count += 1
        derived_section = derived_count > len(specs) / 2
        with st.expander(
            f"{section} ({len(specs)})"
            + (" — auto-filled from suburb and type" if derived_section else ""),
            expanded=not derived_section,
        ):
            columns = st.columns(3)
            for index, spec in enumerate(specs):
                with columns[index % 3]:
                    widget(spec)
    submitted = st.form_submit_button("Estimate price", type="primary", use_container_width=True)

if submitted:
    features, report = parse_all(collect())

    for error in report.errors:
        st.error(str(error))
    for warning in report.warnings:
        st.warning(str(warning))

    if not report.ok:
        st.stop()

    st.subheader("Estimates")
    columns = st.columns(len(ESTIMATORS))
    for column, method in zip(columns, ESTIMATORS):
        with column:
            result = method.estimate(features)
            st.caption(method.blurb)
            if result.price is None:
                st.metric(method.label, "unavailable")
                st.info(result.notes)
                continue
            st.metric(
                method.label,
                f"${result.price:,.0f}",
                delta=f"${result.low:,.0f} – ${result.high:,.0f}" if result.has_range else None,
                delta_color="off",
            )
            if result.notes:
                st.caption(result.notes)

    actual = st.session_state.get("actual_price")
    if actual:
        priced = []
        for method in ESTIMATORS:
            price = method.estimate(features).price
            if price is not None:
                priced.append(price)
        st.divider()
        left, right = st.columns(2)
        left.metric("Actual sale price (from CSV)", f"${actual:,.0f}")
        if priced:
            error_pct = (sum(priced) / len(priced) - actual) / actual * 100
            right.metric("Mean estimate", f"${sum(priced) / len(priced):,.0f}", f"{error_pct:+.1f}%")
