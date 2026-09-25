from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

Features = dict[str, Any]


@dataclass(frozen=True)
class Estimate:
    price: float | None
    low: float | None = None
    high: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.price is None and not self.notes:
            raise ValueError("an Estimate without a price must explain why in notes")

    @property
    def has_range(self) -> bool:
        return self.low is not None and self.high is not None

    @classmethod
    def unavailable(cls, reason: str) -> "Estimate":
        return cls(price=None, notes=reason)

    @classmethod
    def needs(cls, *fields: str) -> "Estimate":
        return cls.unavailable("needs " + ", ".join(fields))


class EstimationMethod(Protocol):
    def __call__(self, features: Features) -> Estimate: ...


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    blurb: str
    estimate: EstimationMethod


def require(features: Features, *names: str) -> list[str] | None:
    blank = []
    for name in names:
        if features.get(name) is None:
            blank.append(name)
    return blank or None
