from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from .lookups import BY_SUBURB

from .features import BY_NAME, FEATURE_NAMES, OUTDOOR_NONE, FeatureSpec

NUMERIC_CATEGORIES = {"GARAGE_AREA"}

TRUE_TOKENS = {"1", "1.0", "true", "yes", "y", "t"}
FALSE_TOKENS = {"0", "0.0", "false", "no", "n", "f"}


@dataclass
class Issue:
    name: str
    message: str

    def __str__(self) -> str:
        return f"**{self.name}** — {self.message}"


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _tokens(text: str) -> list[str]:
    tokens = []
    for token in text.split(";"):
        token = token.strip()
        if token:
            tokens.append(token)
    return tokens


def _quoted(items: list[str]) -> str:
    quoted = []
    for item in items:
        quoted.append(f"`{item}`")
    return ", ".join(quoted)


def parse(spec: FeatureSpec, raw: Any) -> tuple[Any, Issue | None]:
    if raw is None:
        return None, None
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None, None
    elif isinstance(raw, (list, tuple)):
        texts = []
        for item in raw:
            texts.append(str(item))
        return (";".join(texts) or None), None

    text = str(raw).strip()

    if spec.kind in ("number", "integer"):
        try:
            value = float(text)
        except ValueError:
            return None, Issue(spec.name, f"`{text}` is not a number")
        if not math.isfinite(value):
            return None, Issue(spec.name, f"`{text}` is not a finite number")
        if spec.kind == "integer":
            if value != int(value):
                return None, Issue(spec.name, f"`{text}` must be a whole number")
            return int(value), None
        return value, None

    if spec.kind in ("binary", "tristate"):
        low = text.lower()
        if low in TRUE_TOKENS:
            return 1, None
        if low in FALSE_TOKENS:
            return 0, None
        return None, Issue(spec.name, f"`{text}` is not a 0/1 flag")

    if spec.kind == "category":
        match = _match_choice(spec, text)
        if match is None:
            return None, Issue(
                spec.name, f"`{text}` is not one of: {', '.join(spec.choices)}"
            )
        if spec.name in NUMERIC_CATEGORIES:
            return float(match), None
        return match, None

    if spec.kind == "multiselect":
        tokens = _tokens(text)
        if tokens == [OUTDOOR_NONE]:
            return OUTDOOR_NONE, None
        unknown = []
        for token in tokens:
            if token not in spec.choices and token != OUTDOOR_NONE:
                unknown.append(token)
        if unknown:
            return None, Issue(spec.name, f"unknown value(s) {_quoted(unknown)}")
        return (";".join(tokens) or None), None

    if spec.kind in ("date_list", "number_list"):
        tokens = _tokens(text)
        if not tokens:
            return None, None
        bad = []
        for token in tokens:
            if not _parses_as(spec.kind, token):
                bad.append(token)
        if bad:
            what = (
                "a date in YYYY-MM-DD form"
                if spec.kind == "date_list"
                else "a finite number"
            )
            return None, Issue(
                spec.name,
                f"{_quoted(bad)} is not {what}. "
                "Separate each prior sale with `;`.",
            )
        return ";".join(tokens), None

    if spec.kind == "date":
        if isinstance(raw, date):
            return raw.isoformat(), None
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat(), None
        except ValueError:
            return None, Issue(spec.name, f"`{text}` is not a date in YYYY-MM-DD form")

    return text, None


def _parses_as(kind: str, token: str) -> bool:
    try:
        if kind == "number_list":
            return math.isfinite(float(token))
        datetime.strptime(token, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _match_choice(spec: FeatureSpec, text: str) -> str | None:
    for choice in spec.choices:
        if text == choice or text.lower() == choice.lower():
            return choice
        try:
            if float(text) == float(choice):
                return choice
        except ValueError:
            pass
    return None


def range_warning(spec: FeatureSpec, value: Any) -> Issue | None:
    if value is None or spec.lo is None or not spec.is_numeric:
        return None
    slack = abs(spec.hi - spec.lo) * 1e-9
    if spec.lo - slack <= value <= spec.hi + slack:
        return None
    unit = f" {spec.unit}" if spec.unit else ""
    return Issue(
        spec.name,
        f"{value:,g}{unit} is outside the range seen in the dataset "
        f"({spec.lo:,g}–{spec.hi:,g}{unit}). Estimating anyway.",
    )


def validate(features: dict[str, Any], unparsed: frozenset[str] = frozenset()) -> Report:
    report = Report()
    for name in FEATURE_NAMES:
        warning = range_warning(BY_NAME[name], features.get(name))
        if warning:
            report.warnings.append(warning)
    report.warnings.extend(_cross_field(features))
    if not unparsed & HISTORY_FIELDS:
        report.errors.extend(_history_errors(features))
    return report


HISTORY_FIELDS = frozenset({"PREV_SALE_DATE", "PREV_SALE_PRICE", "SALE_DATE"})


def _history_items(raw: Any) -> list[str]:
    return raw.split(";") if raw else []


def _history_errors(features: dict[str, Any]) -> list[Issue]:
    dates = _history_items(features.get("PREV_SALE_DATE"))
    prices = _history_items(features.get("PREV_SALE_PRICE"))

    if len(dates) != len(prices):
        return [
            Issue(
                "PREV_SALE_PRICE",
                f"the sale history has {len(dates)} date(s) but {len(prices)} "
                "price(s). They are paired in order, so each prior sale needs both.",
            )
        ]

    issues: list[Issue] = []

    issues.extend(_history_date_errors(dates, features.get("SALE_DATE")))

    repeated = []
    for value in dates:
        if dates.count(value) > 1 and value not in repeated:
            repeated.append(value)
    repeated.sort()
    if repeated:
        issues.append(
            Issue(
                "PREV_SALE_DATE",
                f"{_quoted(repeated)} appears more than once. "
                "Two sales on one date leave no interval between them, so the "
                "growth rates cannot be worked out. Keep the later sale.",
            )
        )

    unusable = []
    for price in prices:
        if not _is_usable_price(price):
            unusable.append(price)
    if unusable:
        issues.append(
            Issue(
                "PREV_SALE_PRICE",
                f"{_quoted(unusable)} is not a sale price. "
                "Every prior sale needs a finite price above zero -- the "
                "percentage change from zero is undefined.",
            )
        )

    return issues


def _is_usable_price(text: str) -> bool:
    try:
        value = float(text)
    except ValueError:
        return False
    return math.isfinite(value) and value > 0


def _history_date_errors(dates: list[str], sale_date: Any) -> list[Issue]:
    limit = _as_date(sale_date)

    if limit is not None:
        offenders = []
        for text in dates:
            value = _as_date(text)
            if value is not None and value >= limit:
                offenders.append(text)
        if offenders:
            return [
                Issue(
                    "PREV_SALE_DATE",
                    f"{_quoted(offenders)} is not before the "
                    f"sale date ({sale_date}). A prior sale has to predate the sale "
                    "being priced.",
                )
            ]
        return []

    today = date.today()
    offenders = []
    for text in dates:
        value = _as_date(text)
        if value is not None and value > today:
            offenders.append(text)
    if offenders:
        return [
            Issue(
                "PREV_SALE_DATE",
                f"{_quoted(offenders)} is in the future. "
                "Enter the SALE_DATE as well if you are pricing a past sale.",
            )
        ]
    return []


def _as_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _cross_field(features: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []

    built, renovated = features.get("BUILT_YEAR"), features.get("RENOVATION_YEAR")
    if built is not None and renovated is not None and renovated < built:
        issues.append(
            Issue("RENOVATION_YEAR", f"{renovated} is before the build year ({built}).")
        )

    suburb, postcode = features.get("SUBURB"), features.get("POSTCODE")
    if suburb in BY_SUBURB and postcode is not None:
        expected = BY_SUBURB[suburb]["POSTCODE"]
        if str(postcode) != str(expected):
            issues.append(
                Issue("POSTCODE", f"{postcode} is not the postcode for {suburb} ({expected}).")
            )

    return issues


def parse_all(raw: dict[str, Any]) -> tuple[dict[str, Any], Report]:
    features = dict.fromkeys(FEATURE_NAMES)
    report = Report()
    unparsed: set[str] = set()
    for name in FEATURE_NAMES:
        value, error = parse(BY_NAME[name], raw.get(name))
        features[name] = value
        if error:
            report.errors.append(error)
            unparsed.add(name)
    checks = validate(features, frozenset(unparsed))
    report.errors.extend(checks.errors)
    report.warnings.extend(checks.warnings)
    return features, report
