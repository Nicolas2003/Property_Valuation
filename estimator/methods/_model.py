from __future__ import annotations

from ..contract import Estimate, Features, require
from ..ml import blank_inputs, saved_models, to_saved_frame

REQUIRED = ("SUBURB", "PROPERTY_TYPE", "LAND_SIZE", "NUM_BEDROOMS")


def estimate_with(model_key: str, features: Features) -> Estimate:
    missing = require(features, *REQUIRED)
    if missing:
        return Estimate.needs(*missing)

    model = saved_models()[model_key]
    price = model.predict(to_saved_frame(features, model))[0]
    blank, total = blank_inputs(features, model)
    note = (
        f"{blank} of {total} inputs left blank, filled from the training set."
        if blank
        else f"All {total} inputs answered."
    )
    return Estimate(price=float(price), notes=note)
